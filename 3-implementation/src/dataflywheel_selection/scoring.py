"""Turning the four signals into one number.

A weighted sum rather than a learned ranker: every pick can be explained, and
it works from the first cycle, when there is no history to learn from.
"""

from __future__ import annotations

from .config import SelectionConfig
from .models import Clip, ScoredClip, SignalScores
from .signals import (
    conflict_signal,
    quality_multiplier,
    rare_signal,
    unsure_signal,
    wrong_signal,
)


def score_clip(
    clip: Clip,
    config: SelectionConfig,
    scenario_freq: dict[str, float],
) -> ScoredClip:
    """Compute every signal for one clip and combine them into a base score."""
    signals = SignalScores(
        wrong=wrong_signal(clip, config),
        unsure=unsure_signal(clip),
        conflict=conflict_signal(clip, config),
        rare=rare_signal(clip, scenario_freq),
    )
    quality = quality_multiplier(clip, config)
    base = _combine(signals, config) * quality

    return ScoredClip(
        clip_id=clip.clip_id,
        vehicle_id=clip.vehicle_id,
        session_id=clip.session_id,
        site=clip.site,
        duration_s=clip.duration_s,
        scenario_tags=sorted(set(clip.scenario_tags)),
        signals=signals,
        quality_multiplier=round(quality, 4),
        base_score=round(base, 6),
        reasons=_reasons(clip, signals, quality, config),
    )


def _combine(signals: SignalScores, config: SelectionConfig) -> float:
    """Weighted mean over whichever signals we actually have.

    Treating a missing signal as zero would push a clip down just because
    fewer subsystems were reporting. Reweighting avoids that, and it is why
    the same code works at cold start and on a vehicle with bad clocks.
    """
    weights = config.weights.model_dump()
    available = {
        name: value
        for name, value in signals.model_dump().items()
        if value is not None and weights.get(name, 0.0) > 0.0
    }
    if not available:
        return 0.0

    total_weight = sum(weights[name] for name in available)
    return sum(weights[name] * value for name, value in available.items()) / total_weight


def _reasons(clip: Clip, signals: SignalScores, quality: float, config: SelectionConfig) -> list[str]:
    """Why this clip scored what it did, in plain words.

    For whoever later asks what we paid for.
    """
    reasons: list[str] = []

    if signals.wrong:
        # Name the event whenever one was logged. The must-take threshold decides
        # what is bought unconditionally, not what is worth telling the reader —
        # a near-miss just under the threshold is not "a minor event".
        kinds = ", ".join(sorted(e.type.replace("_", " ") for e in clip.events))
        reasons.append(f"the vehicle logged: {kinds}")

    if signals.unsure is not None and signals.unsure >= 0.60:
        reasons.append("the model was unsure")
    if signals.conflict is not None and signals.conflict >= 0.50:
        reasons.append("camera and LiDAR disagreed")
    if signals.rare is not None and signals.rare >= 0.90:
        reasons.append("an uncommon situation")

    # The dangerous case, called out explicitly because it is the one no
    # uncertainty-based method can see: the model is confident and wrong.
    if (
        signals.unsure is not None
        and signals.unsure < 0.30
        and ((signals.conflict or 0.0) >= 0.50 or (signals.wrong or 0.0) >= config.must_take_threshold)
    ):
        reasons.append("DANGEROUS — the model was confident, and the evidence says it was wrong")

    if signals.unsure is None:
        reasons.append("no model scores yet (cold start)")
    if signals.conflict is None and clip.cross_sensor is not None:
        reasons.append("sensor clocks out of sync, so that check was skipped")
    if quality < 0.60:
        reasons.append(f"picture quality is poor ({quality:.2f})")

    return reasons
