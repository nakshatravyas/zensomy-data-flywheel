"""Shared fixtures and builders.

`make_clip` keeps each test readable by naming only the fields that test is
actually about. A test that spells out twenty irrelevant fields hides which one
it is asserting on.
"""

from __future__ import annotations

import math
import random

import pytest

from dataflywheel_selection.config import SelectionConfig
from dataflywheel_selection.models import Clip

DIM = 8


def unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [v / norm for v in vector]


def make_clip(
    clip_id: str = "c0001",
    *,
    vehicle_id: str = "veh01",
    session_id: str = "S-0001",
    duration_s: float = 10.0,
    events: list[dict] | None = None,
    confidence: dict | None = None,
    disagreement: float | None = None,
    clock_sync_ms: float | None = 5.0,
    tags: list[str] | None = None,
    quality: dict | None = None,
    embedding: list[float] | None = None,
    already_labelled: bool = False,
) -> Clip:
    payload: dict = {
        "clip_id": clip_id,
        "vehicle_id": vehicle_id,
        "session_id": session_id,
        "duration_s": duration_s,
        "events": events or [],
        "scenario_tags": tags or ["clear_day"],
        "quality": quality or {},
        "embedding": embedding if embedding is not None else unit([1.0] + [0.0] * (DIM - 1)),
        "already_labelled": already_labelled,
        "clock_sync_ms": clock_sync_ms,
    }
    if confidence is not None:
        payload["model_confidence"] = confidence
    if disagreement is not None:
        payload["cross_sensor"] = {"disagreement_rate": disagreement}
    return Clip.model_validate(payload)


def ordinary(clip_id: str, seed: int, vehicle: str | None = None) -> Clip:
    """A clip the autonomy stack already handles — the bulk of any real corpus.

    Spread across a five-machine fleet by default. Putting a whole synthetic
    corpus on one vehicle would make the per-vehicle cap, not the scoring,
    decide the outcome of every test.
    """
    rng = random.Random(seed)
    return make_clip(
        clip_id,
        vehicle_id=vehicle if vehicle is not None else f"veh{seed % 5:02d}",
        confidence={"min_top1": 0.95, "mean_margin": 0.9, "detection_instability": 0.01},
        disagreement=0.05,
        tags=["clear_day", "flat_terrain"],
        embedding=unit([rng.gauss(0, 1) for _ in range(DIM)]),
    )


@pytest.fixture
def config() -> SelectionConfig:
    """Small budget so that selection pressure is real in every test."""
    return SelectionConfig(budget_hours=0.05, seed=42)  # 180 s = 18 clips
