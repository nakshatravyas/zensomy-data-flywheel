"""Budget allocation: the three buckets, and the caps that bound them."""

from __future__ import annotations

from dataflywheel_selection.config import SelectionConfig
from dataflywheel_selection.pipeline import run_selection
from tests.conftest import make_clip, ordinary, unit


def _failure(clip_id: str, vehicle: str | None = None, seed: int = 0):
    import random

    rng = random.Random(seed)
    return make_clip(
        clip_id,
        vehicle_id=vehicle if vehicle is not None else f"veh{seed % 5:02d}",
        events=[{"type": "disengagement", "severity": 1.0}],
        confidence={"min_top1": 0.4, "mean_margin": 0.15, "detection_instability": 0.4},
        disagreement=0.5,
        tags=["dust"],
        embedding=unit([rng.gauss(0, 1) for _ in range(8)]),
    )


class TestBudgetBounds:
    def test_budget_is_never_exceeded(self, config: SelectionConfig) -> None:
        clips = [ordinary(f"c{i:03d}", seed=i) for i in range(200)]
        result = run_selection(clips, config)
        assert result.selected_seconds <= result.budget_seconds

    def test_small_corpus_is_fully_selected(self, config: SelectionConfig) -> None:
        clips = [ordinary(f"c{i}", seed=i) for i in range(3)]
        result = run_selection(clips, config)
        assert result.funnel.selected == 3


class TestBuckets:
    def test_all_three_buckets_are_used(self, config: SelectionConfig) -> None:
        clips = [_failure(f"f{i}", seed=100 + i) for i in range(4)]
        clips += [ordinary(f"c{i:03d}", seed=i) for i in range(150)]
        result = run_selection(clips, config)

        buckets = {clip.bucket for clip in result.selected}
        assert {"must_take", "scored", "random"} <= buckets

    def test_logged_failures_are_never_crowded_out(self, config: SelectionConfig) -> None:
        # A disengagement is the strongest evidence in the system. It must not
        # lose its place to a high-scoring ordinary clip.
        clips = [_failure("critical", seed=1)]
        clips += [ordinary(f"c{i:03d}", seed=i) for i in range(500)]
        result = run_selection(clips, config)

        selected = {clip.clip_id for clip in result.selected}
        assert "critical" in selected

    def test_random_bucket_takes_clips_the_score_would_reject(
        self, config: SelectionConfig
    ) -> None:
        # Its purpose: if every labelled clip was chosen because the model
        # struggled, ordinary-condition performance becomes unmeasurable.
        clips = [ordinary(f"c{i:03d}", seed=i) for i in range(300)]
        result = run_selection(clips, config)
        assert any(clip.bucket == "random" for clip in result.selected)


class TestCapsAreReportedNotSilent:
    def test_per_vehicle_cap_is_enforced(self) -> None:
        config = SelectionConfig(budget_hours=0.1, per_vehicle_cap=0.2, seed=5)
        # One vehicle supplies every interesting clip in the corpus.
        clips = [_failure(f"v1_{i}", vehicle="veh01", seed=i) for i in range(40)]
        clips += [ordinary(f"v2_{i}", seed=500 + i, vehicle="veh02") for i in range(40)]
        clips += [ordinary(f"v3_{i}", seed=900 + i, vehicle="veh03") for i in range(40)]

        result = run_selection(clips, config)
        # Three vehicles present, so the effective cap is max(0.2, 1/3) = 1/3.
        limit = result.budget_seconds / 3.0
        assert result.per_vehicle_seconds.get("veh01", 0.0) <= limit + 1e-6
        # The interesting vehicle still does not take the whole budget.
        assert result.per_vehicle_seconds["veh01"] < result.selected_seconds

    def test_vehicles_hitting_the_cap_are_counted(self) -> None:
        config = SelectionConfig(budget_hours=0.1, per_vehicle_cap=0.1, seed=5)
        # Ten vehicles, so the configured 10% cap is the binding one.
        clips = [_failure(f"v{i % 10}_{i}", vehicle=f"veh{i % 10:02d}", seed=i) for i in range(200)]
        result = run_selection(clips, config)
        # A silent cap reads as full coverage when it is not.
        assert result.funnel.vehicles_at_cap > 0

    def test_deferred_must_takes_are_counted(self) -> None:
        config = SelectionConfig(budget_hours=0.05, must_take_share=0.2, seed=5)
        clips = [_failure(f"f{i}", vehicle=f"veh{i % 5:02d}", seed=i) for i in range(50)]
        result = run_selection(clips, config)
        assert result.funnel.must_take_deferred_over_share > 0


class TestDiversityUnderBudget:
    def test_one_cluster_cannot_consume_the_budget(self) -> None:
        """The core argument for diversity selection, as an executable claim."""
        config = SelectionConfig(budget_hours=0.05, must_take_share=0.0, scored_share=1.0,
                                 random_share=0.0, seed=11)

        # One dusty afternoon: 150 near-identical, genuinely difficult clips.
        cluster = [
            make_clip(
                f"dust{i:03d}",
                vehicle_id=f"veh{i % 5:02d}",
                confidence={"min_top1": 0.35, "mean_margin": 0.1, "detection_instability": 0.5},
                disagreement=0.6,
                tags=["dust"],
                embedding=unit([1.0, 0.02 * (i % 3), 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]),
            )
            for i in range(150)
        ]
        # A handful of genuinely different difficult scenes, each scoring lower.
        import random

        others = []
        for i in range(10):
            rng = random.Random(2000 + i)
            others.append(
                make_clip(
                    f"other{i}",
                    vehicle_id=f"veh{i % 5:02d}",
                    confidence={"min_top1": 0.6, "mean_margin": 0.3, "detection_instability": 0.2},
                    disagreement=0.3,
                    tags=["wet_ground"],
                    embedding=unit([rng.gauss(0, 1) for _ in range(8)]),
                )
            )

        result = run_selection(cluster + others, config)
        picked_other = sum(1 for c in result.selected if c.clip_id.startswith("other"))

        assert picked_other > 0, "pure ranking would have spent everything on the dust cluster"
        assert len(result.scenario_coverage) > 1
