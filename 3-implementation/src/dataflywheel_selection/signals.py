"""The four difficulty signals, and the quality multiplier.

Each signal asks "is there evidence this moment was hard?" without using
ground truth — which is the thing we have not paid for yet. They are
deliberately independent, because each catches something the others cannot:

    WRONG     the vehicle logged a failure       works with no model
    UNSURE    the model was not confident        needs a model
    CONFLICT  camera and LiDAR disagreed         needs synced clocks
    RARE      uncommon scenario                  relative to the corpus

A signal returns None when it cannot be computed. Missing and zero mean
opposite things, so scoring reweights instead of filling in a zero.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable

from .config import SelectionConfig
from .models import Clip


def wrong_signal(clip: Clip, config: SelectionConfig) -> float:
    """Worst thing the vehicle logged during this clip.

    Comes from the control systems, not a model — so it works from day one.
    """
    if not clip.events:
        return 0.0
    return max(
        config.event_weights.get(event.type, 0.0) * event.severity
        for event in clip.events
    )


def unsure_signal(clip: Clip) -> float | None:
    """How unsure the model was.

    A narrow gap between the top two classes means real ambiguity. Low
    confidence on its own can just mean the model is badly calibrated.
    """
    mc = clip.model_confidence
    if mc is None:
        return None
    low_confidence = 1.0 - mc.min_top1
    narrow_margin = 1.0 - mc.mean_margin
    return _clamp(0.45 * low_confidence + 0.35 * narrow_margin + 0.20 * mc.detection_instability)


def conflict_signal(clip: Clip, config: SelectionConfig) -> float | None:
    """How much the sensors disagreed — if their clocks can be trusted.

    200 ms of drift is 0.56 m at 10 km/h, enough to make working sensors look
    like they disagree on every frame. Skip the clock check and a timing fault
    becomes a fleet-wide false alarm.
    """
    if clip.cross_sensor is None:
        return None

    skew = clip.clock_sync_ms
    if skew is None:
        # Synchronisation quality unknown. Absence of evidence is not evidence
        # of synchronisation, so the signal is withheld rather than assumed.
        return None
    if skew >= config.clock_sync_disable_ms:
        return None

    if skew <= config.clock_sync_trust_ms:
        trust = 1.0
    else:
        span = config.clock_sync_disable_ms - config.clock_sync_trust_ms
        trust = 1.0 - (skew - config.clock_sync_trust_ms) / span

    return _clamp(clip.cross_sensor.disagreement_rate * trust)


def scenario_frequencies(clips: Iterable[Clip]) -> dict[str, float]:
    """How common each scenario tag is in this corpus.

    Rare means rare compared to what else we collected — not an absolute.
    """
    counts: Counter[str] = Counter()
    total = 0
    for clip in clips:
        total += 1
        for tag in set(clip.scenario_tags):
            counts[tag] += 1
    if total == 0:
        return {}
    return {tag: count / total for tag, count in counts.items()}


def rare_signal(clip: Clip, frequencies: dict[str, float]) -> float:
    """How uncommon this clip's rarest scenario is.

    No tags scores zero, not one — nothing recognised means nothing notable,
    not something exotic.
    """
    if not clip.scenario_tags or not frequencies:
        return 0.0
    rarest = min(frequencies.get(tag, 0.0) for tag in set(clip.scenario_tags))
    return _clamp(1.0 - rarest)


def quality_multiplier(clip: Clip, config: SelectionConfig) -> float:
    """How usable the data is, as a multiplier on the whole score.

    A broken sensor looks maximally interesting — high uncertainty and high
    disagreement at once. Subtracting a penalty would be outvoted by four
    strong signals. Multiplying cannot be.
    """
    q = clip.quality
    base = 1.0 - q.blur - q.exposure_clipping - q.dropped_frame_rate
    if q.sensor_fault:
        base *= config.sensor_fault_multiplier
    return max(config.quality_floor, _clamp(base))


def _clamp(value: float, low: float = 0.0, high: float = 1.0) -> float:
    return max(low, min(high, value))
