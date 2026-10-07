"""The whole thing: filter, score, allocate.

Each step is pure with respect to the one before it, which is what lets the
tests assert the design's promises instead of just describing them.
"""

from __future__ import annotations

from collections import Counter

import numpy as np

from .budget import allocate
from .config import SelectionConfig
from .diversity import DiversityIndex
from .io import embedding_matrix
from .models import Clip, DroppedClip, FunnelCounts, ScoredClip, SelectionResult
from .scoring import score_clip
from .signals import quality_multiplier, scenario_frequencies


def run_selection(clips: list[Clip], config: SelectionConfig) -> SelectionResult:
    """Pick the clips most worth labelling, within the budget."""
    funnel = FunnelCounts(input_clips=len(clips))

    eligible, dropped = _filter(clips, config, funnel)
    if not eligible:
        return _empty_result(config, funnel, dropped)

    # Rarity is measured against what is still on the table — clips we already
    # labelled are not part of the coverage question any more.
    frequencies = scenario_frequencies(eligible)
    scored = [score_clip(clip, config, frequencies) for clip in eligible]
    funnel.scored = len(scored)

    budget_seconds = config.budget_seconds(sum(c.duration_s for c in eligible))

    index = DiversityIndex(
        embedding_matrix(eligible),
        threshold=config.similarity_threshold,
        min_attenuation=config.min_attenuation,
    )

    selected = allocate(scored, index, config, funnel, budget_seconds)
    funnel.selected = len(selected)

    return SelectionResult(
        config=config.model_dump(mode="json"),
        funnel=funnel,
        budget_seconds=round(budget_seconds, 3),
        selected_seconds=round(sum(c.duration_s for c in selected), 3),
        selected=selected,
        dropped=dropped,
        signal_availability=_availability(scored),
        per_vehicle_seconds=_per_vehicle(selected),
        scenario_coverage=_coverage(selected),
    )


def _filter(
    clips: list[Clip], config: SelectionConfig, funnel: FunnelCounts
) -> tuple[list[Clip], list[DroppedClip]]:
    """Drop what cannot be labelled usefully. Record every drop.

    Two reasons only. Already labelled — paying twice buys nothing. Quality
    too low — a clip the sensor could not capture teaches the model about the
    sensor. It is a floor, not a preference: a dusty lens is kept and flagged,
    because dust is what the fleet has to handle.
    """
    eligible: list[Clip] = []
    dropped: list[DroppedClip] = []

    for clip in clips:
        if clip.already_labelled:
            funnel.dropped_already_labelled += 1
            dropped.append(DroppedClip(clip_id=clip.clip_id, reason="already_labelled"))
            continue

        quality = quality_multiplier(clip, config)
        if quality < config.min_quality:
            funnel.dropped_low_quality += 1
            dropped.append(
                DroppedClip(
                    clip_id=clip.clip_id,
                    reason=f"quality {quality:.3f} below minimum {config.min_quality:.3f}",
                )
            )
            continue

        eligible.append(clip)

    return eligible, dropped


def _availability(scored: list[ScoredClip]) -> dict[str, int]:
    counts = {"wrong": 0, "unsure": 0, "conflict": 0, "rare": 0}
    for clip in scored:
        for name, value in clip.signals.model_dump().items():
            if value is not None:
                counts[name] += 1
    return counts


def _per_vehicle(selected: list[ScoredClip]) -> dict[str, float]:
    totals: dict[str, float] = {}
    for clip in selected:
        totals[clip.vehicle_id] = round(totals.get(clip.vehicle_id, 0.0) + clip.duration_s, 3)
    return totals


def _coverage(selected: list[ScoredClip]) -> dict[str, int]:
    counter: Counter[str] = Counter()
    for clip in selected:
        counter.update(set(clip.scenario_tags))
    return dict(counter)


def _empty_result(
    config: SelectionConfig, funnel: FunnelCounts, dropped: list[DroppedClip]
) -> SelectionResult:
    return SelectionResult(
        config=config.model_dump(mode="json"),
        funnel=funnel,
        budget_seconds=round(budget_seconds, 3),
        selected_seconds=0.0,
        selected=[],
        dropped=dropped,
        signal_availability={"wrong": 0, "unsure": 0, "conflict": 0, "rare": 0},
        per_vehicle_seconds={},
        scenario_coverage={},
    )


__all__ = ["run_selection"]
