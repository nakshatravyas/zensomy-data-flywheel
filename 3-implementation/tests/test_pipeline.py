"""End-to-end behaviour, determinism, and the input trust boundary."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

from dataflywheel_selection.config import SelectionConfig
from dataflywheel_selection.io import InputError, read_clips, write_result
from dataflywheel_selection.pipeline import run_selection
from tests.conftest import make_clip, ordinary

DATA = Path(__file__).resolve().parents[1] / "data"
EXAMPLE_INPUT = DATA / "example_input.jsonl"
COLD_START_INPUT = DATA / "cold_start.jsonl"


class TestFiltering:
    def test_already_labelled_clips_are_excluded_and_recorded(
        self, config: SelectionConfig
    ) -> None:
        clips = [ordinary(f"c{i}", seed=i) for i in range(5)]
        clips.append(make_clip("seen", already_labelled=True))
        result = run_selection(clips, config)

        assert "seen" not in {c.clip_id for c in result.selected}
        assert result.funnel.dropped_already_labelled == 1
        assert any(d.reason == "already_labelled" for d in result.dropped)

    def test_unusable_clips_are_dropped_with_a_stated_reason(
        self, config: SelectionConfig
    ) -> None:
        unusable = make_clip(
            "broken",
            quality={"blur": 0.95, "exposure_clipping": 0.5, "sensor_fault": True},
        )
        result = run_selection([unusable, *[ordinary(f"c{i}", seed=i) for i in range(3)]], config)
        assert result.funnel.dropped_low_quality == 1
        assert "quality" in result.dropped[0].reason

    def test_a_dusty_lens_is_kept_not_dropped(self, config: SelectionConfig) -> None:
        # Dust is the operating condition, not a defect. Only genuinely
        # unusable data is cut.
        dusty = make_clip("dusty", quality={"blur": 0.2}, tags=["dust"])
        result = run_selection([dusty, ordinary("c1", seed=1)], config)
        assert "dusty" in {c.clip_id for c in result.selected}

    def test_every_input_clip_is_accounted_for(self, config: SelectionConfig) -> None:
        """Nothing may vanish between the input count and the funnel."""
        clips = [ordinary(f"c{i}", seed=i) for i in range(40)]
        clips.append(make_clip("labelled", already_labelled=True))
        clips.append(make_clip("broken", quality={"blur": 1.0, "sensor_fault": True}))
        f = run_selection(clips, config).funnel
        assert f.input_clips == f.dropped_already_labelled + f.dropped_low_quality + f.scored


class TestDeterminism:
    def test_same_input_and_seed_produce_identical_output(
        self, config: SelectionConfig
    ) -> None:
        clips = [ordinary(f"c{i:03d}", seed=i) for i in range(120)]
        first = run_selection(clips, config)
        second = run_selection([ordinary(f"c{i:03d}", seed=i) for i in range(120)], config)

        assert [c.clip_id for c in first.selected] == [c.clip_id for c in second.selected]
        assert [c.rank for c in first.selected] == [c.rank for c in second.selected]

    def test_the_seed_does_not_reach_the_must_take_bucket(self) -> None:
        """Logged failures are chosen before the seed is consulted.

        The seed governs the random reservation, which is drawn before the
        scored bucket — so it does legitimately change what scoring sees. What
        it must never change is which logged failures get annotated.
        """
        clips = [ordinary(f"c{i:03d}", seed=i) for i in range(200)]
        clips.append(
            make_clip("failure", events=[{"type": "disengagement", "severity": 1.0}])
        )
        must = lambda r: sorted(c.clip_id for c in r.selected if c.bucket == "must_take")

        a = run_selection(clips, SelectionConfig(budget_hours=0.05, seed=1))
        b = run_selection(clips, SelectionConfig(budget_hours=0.05, seed=2))
        assert must(a) == must(b) == ["failure"]

    def test_input_order_does_not_change_the_selection(self, config: SelectionConfig) -> None:
        clips = [ordinary(f"c{i:03d}", seed=i) for i in range(80)]
        forward = run_selection(list(clips), config)
        backward = run_selection(list(reversed(clips)), config)
        assert sorted(c.clip_id for c in forward.selected) == sorted(
            c.clip_id for c in backward.selected
        )


class TestInputIsATrustBoundary:
    def test_malformed_json_names_the_line(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.jsonl"
        good = json.dumps({"clip_id": "a", "vehicle_id": "v", "session_id": "s", "duration_s": 10})
        bad.write_text(good + "\nnot json\n", encoding="utf-8")
        with pytest.raises(InputError, match=":2:"):
            read_clips(bad)

    def test_invalid_record_names_the_field(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.jsonl"
        bad.write_text(
            json.dumps({"clip_id": "a", "vehicle_id": "v", "session_id": "s", "duration_s": -1})
            + "\n",
            encoding="utf-8",
        )
        with pytest.raises(InputError, match="duration_s"):
            read_clips(bad)

    def test_duplicate_clip_ids_are_rejected(self, tmp_path: Path) -> None:
        record = {"clip_id": "a", "vehicle_id": "v", "session_id": "s", "duration_s": 10}
        bad = tmp_path / "dupe.jsonl"
        bad.write_text(json.dumps(record) + "\n" + json.dumps(record) + "\n", encoding="utf-8")
        with pytest.raises(InputError, match="duplicate"):
            read_clips(bad)

    def test_empty_input_is_an_error_not_an_empty_selection(self, tmp_path: Path) -> None:
        empty = tmp_path / "empty.jsonl"
        empty.write_text("\n\n", encoding="utf-8")
        with pytest.raises(InputError, match="no records"):
            read_clips(empty)

    def test_missing_file_is_reported_clearly(self, tmp_path: Path) -> None:
        with pytest.raises(InputError, match="not found"):
            read_clips(tmp_path / "nope.jsonl")


class TestAgainstTheCommittedExample:
    def test_example_corpus_runs_end_to_end(self, tmp_path: Path) -> None:
        clips = read_clips(EXAMPLE_INPUT)
        config = SelectionConfig(seed=1337)
        result = run_selection(clips, config)

        assert result.funnel.input_clips == 6000
        assert result.selected_seconds <= result.budget_seconds
        assert len(result.scenario_coverage) >= 3, "selection is not monocultural"

        paths = write_result(result, tmp_path, input_digest="deadbeef")
        assert paths["report"].exists()
        assert paths["selected"].exists()
        assert paths["manifest"].exists()

        manifest = json.loads(paths["manifest"].read_text())
        assert manifest["input_sha256"] == "deadbeef"
        assert manifest["config"]["seed"] == 1337

    def test_faulty_vehicle_does_not_dominate(self) -> None:
        """A machine with a broken sensor cannot buy the budget.

        veh05 has a degraded sensor for part of the corpus, which makes it score
        maximally on every difficulty signal at once — maximum uncertainty,
        maximum cross-sensor disagreement, a rare tag. Two mechanisms hold it
        back: the quality multiplier suppresses the faulty clips themselves, and
        the per-vehicle cap bounds the machine as a whole.
        """
        clips = read_clips(EXAMPLE_INPUT)
        result = run_selection(clips, SelectionConfig(budget_hours=0.1, seed=1337))

        shares = result.per_vehicle_seconds
        faulty_share = shares.get("veh05", 0.0)

        # Five vehicles present, so the effective cap is max(0.15, 1/5) = 0.20.
        assert faulty_share <= result.budget_seconds * 0.20 + 1e-6
        assert faulty_share <= max(shares.values()), "faulty machine does not exceed the fleet"

    def test_cli_runs_and_writes_output(self, tmp_path: Path) -> None:
        completed = subprocess.run(
            [
                sys.executable, "-m", "dataflywheel_selection",
                "--input", str(EXAMPLE_INPUT),
                "--out", str(tmp_path),
            ],
            capture_output=True,
            text=True,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr
        assert (tmp_path / "report.md").exists()
        assert "selected" in completed.stdout

    def test_cli_fails_loudly_on_a_bad_input(self, tmp_path: Path) -> None:
        bad = tmp_path / "bad.jsonl"
        bad.write_text("{oops\n", encoding="utf-8")
        completed = subprocess.run(
            [sys.executable, "-m", "dataflywheel_selection",
             "--input", str(bad), "--out", str(tmp_path / "out")],
            capture_output=True, text=True, check=False,
        )
        assert completed.returncode == 2
        assert "error" in completed.stderr


class TestColdStart:
    """Selection works before any model has been trained."""

    def test_runs_with_no_model_scores_at_all(self) -> None:
        clips = read_clips(COLD_START_INPUT)
        assert all(c.model_confidence is None for c in clips)

        result = run_selection(clips, SelectionConfig(budget_hours=0.1, seed=1337))

        assert result.signal_availability["unsure"] == 0
        assert result.signal_availability["wrong"] > 0, "the strongest signal needs no model"
        assert result.funnel.selected > 0
        assert len(result.scenario_coverage) >= 3

    def test_cold_start_still_prioritises_logged_failures(self) -> None:
        clips = read_clips(COLD_START_INPUT)
        result = run_selection(clips, SelectionConfig(budget_hours=0.1, seed=1337))
        assert any(c.bucket == "must_take" for c in result.selected)
        assert any("cold start" in r for c in result.selected for r in c.reasons)


class TestTheCeilingIsAParameter:
    """The annotation ceiling is an input, not something the design is tuned to.

    The brief's "100 hours" is an illustration. Next quarter it is a different
    number, and as the fleet grows the recorded side grows far faster than the
    annotated side. These tests assert that nothing in the pipeline is built
    around a particular ceiling.
    """

    BUDGETS = (0.02, 0.05, 0.1, 0.2, 0.4)

    def test_scoring_does_not_know_the_budget(self) -> None:
        """What a clip is worth is independent of how much can be afforded."""
        clips = read_clips(EXAMPLE_INPUT)
        small = run_selection(clips, SelectionConfig(budget_hours=0.02, seed=1))
        large = run_selection(clips, SelectionConfig(budget_hours=0.4, seed=1))

        a = {c.clip_id: c.base_score for c in small.selected}
        b = {c.clip_id: c.base_score for c in large.selected}
        shared = set(a) & set(b)
        assert shared, "the two runs should overlap at all"
        assert all(a[k] == b[k] for k in shared)

    def test_logged_failures_are_monotone_in_the_budget(self) -> None:
        """A larger ceiling never drops a failure a smaller one had room for."""
        clips = read_clips(EXAMPLE_INPUT)
        previous: set[str] = set()
        for hours in self.BUDGETS:
            result = run_selection(clips, SelectionConfig(budget_hours=hours, seed=1337))
            must = {c.clip_id for c in result.selected if c.bucket == "must_take"}
            assert previous <= must, f"must-take set shrank at {hours} h"
            previous = must

    def test_selection_scales_with_the_ceiling(self) -> None:
        clips = read_clips(EXAMPLE_INPUT)
        counts = [
            run_selection(clips, SelectionConfig(budget_hours=h, seed=1337)).funnel.selected
            for h in self.BUDGETS
        ]
        assert counts == sorted(counts)
        assert counts[-1] > counts[0] * 10

    def test_a_tiny_ceiling_still_buys_variety(self) -> None:
        """Even at 2% of the worked example, selection is not monocultural."""
        clips = read_clips(EXAMPLE_INPUT)
        result = run_selection(clips, SelectionConfig(budget_hours=0.02, seed=1337))
        assert result.funnel.selected > 0
        assert len(result.scenario_coverage) >= 3
