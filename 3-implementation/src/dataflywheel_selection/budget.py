"""Splitting the budget three ways.

    20%  must-take   the vehicle logged a failure — not negotiable
    70%  scored      best first, lookalikes pushed down
    10%  random      picked blind, on purpose

The random share looks wasteful and is not. If every labelled clip is one the
model struggled with, we can never measure normal driving — and random is the
only thing that finds problems no signal was built to look for.

A per-vehicle cap runs across all three. One machine with a dirty lens would
otherwise take everything, and a machine that keeps hitting the cap is telling
us it needs maintenance.
"""

from __future__ import annotations

import random

import numpy as np

from .config import SelectionConfig
from .diversity import DiversityIndex
from .models import FunnelCounts, ScoredClip


class BudgetLedger:
    """Tracks spending, including the per-vehicle cap.

    The cap is never tighter than an equal split across the vehicles present.
    15% is right for a fleet of tens; on a fleet of five it would cap usage at
    75% and quietly waste a quarter of the budget, since nobody is allowed to
    take the rest. The number limits concentration, not spending.
    """

    def __init__(self, total_seconds: float, per_vehicle_cap: float, vehicle_count: int) -> None:
        self.total = total_seconds
        self.used = 0.0
        effective_cap = max(per_vehicle_cap, 1.0 / max(1, vehicle_count))
        self.effective_cap = effective_cap
        self._vehicle_limit = total_seconds * effective_cap
        self._per_vehicle: dict[str, float] = {}

    def vehicle_has_room(self, clip: ScoredClip) -> bool:
        spent = self._per_vehicle.get(clip.vehicle_id, 0.0)
        return spent + clip.duration_s <= self._vehicle_limit

    def charge(self, clip: ScoredClip) -> None:
        self.used += clip.duration_s
        self._per_vehicle[clip.vehicle_id] = (
            self._per_vehicle.get(clip.vehicle_id, 0.0) + clip.duration_s
        )


def allocate(
    scored: list[ScoredClip],
    index: DiversityIndex,
    config: SelectionConfig,
    funnel: FunnelCounts,
    budget_seconds: float,
) -> list[ScoredClip]:
    """Fill the three buckets, in this order:

        must-take  so a logged failure is never crowded out
        random     a reservation taken last is not reserved — the scored
                   bucket would fill every per-vehicle cap first and leave
                   nothing behind it
        scored     takes everything that remains
    """
    at_cap: set[str] = set()
    ledger = BudgetLedger(
        budget_seconds,
        config.per_vehicle_cap,
        vehicle_count=len({clip.vehicle_id for clip in scored}),
    )
    by_id = {clip.clip_id: position for position, clip in enumerate(scored)}
    taken: set[str] = set()
    selected: list[ScoredClip] = []

    # ---- bucket 1: must-take ------------------------------------------------
    must_ceiling = budget_seconds * config.must_take_share
    candidates = sorted(
        (c for c in scored if (c.signals.wrong or 0.0) >= config.must_take_threshold),
        key=lambda c: (-c.base_score, c.clip_id),
    )
    for clip in candidates:
        if ledger.used + clip.duration_s > must_ceiling:
            funnel.must_take_deferred_over_share += 1
            continue
        if not ledger.vehicle_has_room(clip):
            at_cap.add(clip.vehicle_id)
            continue
        _take(clip, "must_take", index, by_id, ledger, taken, selected)

    # ---- bucket 2: the random reservation ------------------------------------
    random_ceiling = ledger.used + budget_seconds * config.random_share
    remaining_pool = sorted(
        (c for c in scored if c.clip_id not in taken), key=lambda c: c.clip_id
    )
    rng = random.Random(config.seed)
    rng.shuffle(remaining_pool)
    for clip in remaining_pool:
        if ledger.used + clip.duration_s > random_ceiling:
            break
        if not ledger.vehicle_has_room(clip):
            at_cap.add(clip.vehicle_id)
            continue
        _take(clip, "random", index, by_id, ledger, taken, selected)

    # ---- bucket 3: scored, diversity-attenuated ------------------------------
    pool = [c for c in scored if c.clip_id not in taken]
    _greedy_diverse(pool, index, by_id, ledger, taken, selected, budget_seconds, at_cap)

    funnel.vehicles_at_cap = len(at_cap)
    funnel.budget_unspendable_s = round(budget_seconds - ledger.used, 3) if at_cap else 0.0

    for rank, clip in enumerate(
        sorted(selected, key=lambda c: (-(c.effective_score or 0.0), c.clip_id)), start=1
    ):
        clip.rank = rank

    return sorted(selected, key=lambda c: c.rank or 0)


def _greedy_diverse(
    pool: list[ScoredClip],
    index: DiversityIndex,
    by_id: dict[str, int],
    ledger: BudgetLedger,
    taken: set[str],
    selected: list[ScoredClip],
    ceiling: float,
    at_cap: set[str],
) -> None:
    """Take the best clip left, push its lookalikes down, repeat.

    Re-scored after every pick, because what a clip is worth depends on what
    we already bought.

    Sorted by clip_id first: argmax breaks ties by position, so without a
    stable order the answer would depend on how the input file was ordered.
    """
    if not pool:
        return
    pool = sorted(pool, key=lambda c: c.clip_id)
    positions = np.array([by_id[c.clip_id] for c in pool], dtype=np.int64)
    base = np.array([c.base_score for c in pool], dtype=np.float64)
    alive = np.ones(len(pool), dtype=bool)
    shortest = min(c.duration_s for c in pool)

    while alive.any():
        # Stop when nothing fits. Otherwise every remaining clip gets blamed
        # on the cap, and a full budget looks like a cap throwing work away.
        if ledger.used + shortest > ceiling:
            break

        effective = np.where(alive, base * index.attenuation[positions], -np.inf)
        best = int(np.argmax(effective))
        if effective[best] == -np.inf:
            break

        clip = pool[best]
        alive[best] = False

        if ledger.used + clip.duration_s > ceiling:
            # Too big for what is left; a smaller clip might still fit.
            continue
        if not ledger.vehicle_has_room(clip):
            at_cap.add(clip.vehicle_id)
            continue

        _take(clip, "scored", index, by_id, ledger, taken, selected)


def _take(
    clip: ScoredClip,
    bucket: str,
    index: DiversityIndex,
    by_id: dict[str, int],
    ledger: BudgetLedger,
    taken: set[str],
    selected: list[ScoredClip],
) -> None:
    position = by_id[clip.clip_id]
    clip.selected = True
    clip.bucket = bucket  # type: ignore[assignment]
    clip.similarity_divisor = index.divisor(position)
    clip.effective_score = round(clip.base_score * float(index.attenuation[position]), 6)
    ledger.charge(clip)
    taken.add(clip.clip_id)
    selected.append(clip)
    index.mark_selected(position)
