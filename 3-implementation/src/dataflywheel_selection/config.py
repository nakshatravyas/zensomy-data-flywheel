"""Every number that affects a selection decision lives here.

Keeping them in one validated object means a run is fully described by its
config plus its input — which is what makes it reproducible.
"""

from __future__ import annotations

import json
from pathlib import Path

from pydantic import BaseModel, Field, model_validator

# We can label roughly 1% of what we record — 100 hours out of 10,000.
ANNOTATION_RATE = 0.01

# How much each logged event says about difficulty. A disengagement is the
# strongest evidence we have anywhere: an operator judged the machine unsafe.
DEFAULT_EVENT_WEIGHTS: dict[str, float] = {
    "disengagement": 1.00,
    "emergency_brake": 0.90,
    "near_miss": 0.80,
    "mission_abort": 0.80,
    "replan_storm": 0.60,
    "operator_flag": 0.50,
}


class SignalWeights(BaseModel):
    """How much each signal counts.

    Reweighted per clip over whatever is actually available, so a corpus with
    no model scores still ranks sensibly.
    """

    wrong: float = Field(0.35, ge=0.0)
    unsure: float = Field(0.30, ge=0.0)
    conflict: float = Field(0.20, ge=0.0)
    rare: float = Field(0.15, ge=0.0)

    @model_validator(mode="after")
    def _at_least_one_positive(self) -> "SignalWeights":
        if self.wrong + self.unsure + self.conflict + self.rare <= 0:
            raise ValueError("at least one signal weight must be positive")
        return self


class SelectionConfig(BaseModel):
    """Full configuration for one selection run."""

    model_config = {"extra": "forbid"}

    # --- how much we can label --------------------------------------------
    # Left unset in normal use: the limit is ANNOTATION_RATE of the pool.
    # Tests set it directly to make selection pressure explicit.
    budget_hours: float | None = Field(None, gt=0)
    must_take_share: float = Field(0.20, ge=0.0, le=1.0)
    scored_share: float = Field(0.70, ge=0.0, le=1.0)
    random_share: float = Field(0.10, ge=0.0, le=1.0)
    per_vehicle_cap: float = Field(
        0.15, gt=0.0, le=1.0,
        description="Maximum share of the budget any single vehicle may consume.",
    )

    # --- signals ----------------------------------------------------------
    weights: SignalWeights = Field(default_factory=SignalWeights)
    event_weights: dict[str, float] = Field(default_factory=lambda: dict(DEFAULT_EVENT_WEIGHTS))
    must_take_threshold: float = Field(
        0.80, ge=0.0, le=1.0,
        description="WRONG score at or above which a clip is taken unconditionally.",
    )

    # --- clock gate on CONFLICT -------------------------------------------
    # Sensors on drifting clocks look like they disagree when they do not.
    # Below `trust` we believe the comparison, above `disable` we drop it.
    clock_sync_trust_ms: float = Field(10.0, gt=0)
    clock_sync_disable_ms: float = Field(50.0, gt=0)

    # --- quality ----------------------------------------------------------
    sensor_fault_multiplier: float = Field(0.25, ge=0.0, le=1.0)
    min_quality: float = Field(
        0.15, ge=0.0, le=1.0,
        description="Clips below this quality are dropped before scoring.",
    )
    quality_floor: float = Field(0.05, ge=0.0, le=1.0)

    # --- diversity --------------------------------------------------------
    similarity_threshold: float = Field(
        0.85, ge=0.0, le=1.0,
        description="Cosine similarity above which two clips count as near-duplicates.",
    )
    min_attenuation: float = Field(
        0.30, gt=0.0, le=1.0,
        description="Score multiplier applied to a clip identical to one already selected.",
    )

    # --- determinism ------------------------------------------------------
    seed: int = Field(1337, ge=0)

    @model_validator(mode="after")
    def _shares_sum_to_one(self) -> "SelectionConfig":
        total = self.must_take_share + self.scored_share + self.random_share
        if abs(total - 1.0) > 1e-6:
            raise ValueError(f"budget shares must sum to 1.0, got {total:.4f}")
        if self.clock_sync_disable_ms <= self.clock_sync_trust_ms:
            raise ValueError("clock_sync_disable_ms must exceed clock_sync_trust_ms")
        return self

    def budget_seconds(self, pool_seconds: float) -> float:
        """How much footage we can afford to label."""
        if self.budget_hours is not None:
            return self.budget_hours * 3600.0
        return pool_seconds * ANNOTATION_RATE

    @classmethod
    def from_file(cls, path: str | Path) -> "SelectionConfig":
        return cls.model_validate(json.loads(Path(path).read_text(encoding="utf-8")))
