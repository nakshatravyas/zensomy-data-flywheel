"""Input and output schemas.

Input comes from another system, so every record is validated on the way in.
A bad record is reported with its line number, never skipped quietly.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class ClipEvent(BaseModel):
    """A moment the vehicle itself recorded as difficult."""

    model_config = {"extra": "ignore"}

    type: str
    severity: float = Field(1.0, ge=0.0, le=1.0)


class ModelConfidence(BaseModel):
    """What the model reported. Absent before any model exists."""

    model_config = {"extra": "ignore"}

    min_top1: float = Field(..., ge=0.0, le=1.0, description="Lowest top-class confidence across frames.")
    mean_margin: float = Field(..., ge=0.0, le=1.0, description="Mean gap between the top two classes.")
    detection_instability: float = Field(0.0, ge=0.0, le=1.0, description="Objects flickering between frames.")


class CrossSensor(BaseModel):
    """Agreement between independent sensing modalities on the same scene."""

    model_config = {"extra": "ignore"}

    disagreement_rate: float = Field(..., ge=0.0, le=1.0)


class ClipQuality(BaseModel):
    """Whether the data is usable, separate from whether it is interesting."""

    model_config = {"extra": "ignore"}

    blur: float = Field(0.0, ge=0.0, le=1.0)
    exposure_clipping: float = Field(0.0, ge=0.0, le=1.0)
    dropped_frame_rate: float = Field(0.0, ge=0.0, le=1.0)
    sensor_fault: bool = False


class Clip(BaseModel):
    """One candidate clip, as emitted by the catalog."""

    model_config = {"extra": "ignore"}

    clip_id: str = Field(..., min_length=1)
    vehicle_id: str = Field(..., min_length=1)
    session_id: str = Field(..., min_length=1)
    site: str = "unknown"
    start_time: str | None = None
    duration_s: float = Field(..., gt=0.0, le=600.0)

    events: list[ClipEvent] = Field(default_factory=list)
    model_confidence: ModelConfidence | None = None
    cross_sensor: CrossSensor | None = None
    clock_sync_ms: float | None = Field(None, ge=0.0)
    scenario_tags: list[str] = Field(default_factory=list)
    quality: ClipQuality = Field(default_factory=ClipQuality)
    embedding: list[float] = Field(default_factory=list)
    already_labelled: bool = False


Bucket = Literal["must_take", "scored", "random"]


class SignalScores(BaseModel):
    """The four difficulty signals. `None` means "not computable for this clip"."""

    wrong: float | None = None
    unsure: float | None = None
    conflict: float | None = None
    rare: float | None = None


class ScoredClip(BaseModel):
    """A clip, plus everything needed to explain the decision made about it."""

    clip_id: str
    vehicle_id: str
    session_id: str
    site: str
    duration_s: float
    scenario_tags: list[str]

    signals: SignalScores
    quality_multiplier: float
    base_score: float
    reasons: list[str] = Field(default_factory=list)

    # populated during selection
    selected: bool = False
    bucket: Bucket | None = None
    rank: int | None = None
    similarity_divisor: float = 1.0
    effective_score: float | None = None


class DroppedClip(BaseModel):
    """A clip removed before scoring, with the reason recorded."""

    clip_id: str
    reason: str


class FunnelCounts(BaseModel):
    """Counts at every stage, so nothing disappears unexplained."""

    input_clips: int = 0
    dropped_already_labelled: int = 0
    dropped_low_quality: int = 0
    scored: int = 0
    selected: int = 0
    must_take_deferred_over_share: int = 0
    vehicles_at_cap: int = 0
    budget_unspendable_s: float = 0.0


class SelectionResult(BaseModel):
    """The output of one run."""

    config: dict
    funnel: FunnelCounts
    budget_seconds: float
    selected_seconds: float
    selected: list[ScoredClip]
    dropped: list[DroppedClip]
    signal_availability: dict[str, int]
    per_vehicle_seconds: dict[str, float]
    scenario_coverage: dict[str, int]
