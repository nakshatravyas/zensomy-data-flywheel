"""Signal computation, including the conditions under which a signal is withheld."""

from __future__ import annotations

import pytest

from dataflywheel_selection.config import SelectionConfig
from dataflywheel_selection.signals import (
    conflict_signal,
    quality_multiplier,
    rare_signal,
    scenario_frequencies,
    unsure_signal,
    wrong_signal,
)
from tests.conftest import make_clip


class TestWrong:
    def test_no_events_scores_zero(self, config: SelectionConfig) -> None:
        assert wrong_signal(make_clip(), config) == 0.0

    def test_disengagement_is_the_maximum(self, config: SelectionConfig) -> None:
        clip = make_clip(events=[{"type": "disengagement", "severity": 1.0}])
        assert wrong_signal(clip, config) == 1.0

    def test_strongest_event_wins(self, config: SelectionConfig) -> None:
        clip = make_clip(
            events=[
                {"type": "replan_storm", "severity": 1.0},
                {"type": "disengagement", "severity": 1.0},
            ]
        )
        assert wrong_signal(clip, config) == 1.0

    def test_unknown_event_type_is_ignored_not_assumed(self, config: SelectionConfig) -> None:
        # A new event type must not silently acquire a weight.
        clip = make_clip(events=[{"type": "some_future_event", "severity": 1.0}])
        assert wrong_signal(clip, config) == 0.0

    def test_available_without_any_model(self, config: SelectionConfig) -> None:
        clip = make_clip(events=[{"type": "near_miss", "severity": 1.0}], confidence=None)
        assert clip.model_confidence is None
        assert wrong_signal(clip, config) > 0


class TestUnsure:
    def test_absent_without_a_model_score(self) -> None:
        # None, not zero. A missing signal and an absent signal mean opposites.
        assert unsure_signal(make_clip(confidence=None)) is None

    def test_confident_model_scores_low(self) -> None:
        clip = make_clip(confidence={"min_top1": 0.99, "mean_margin": 0.95, "detection_instability": 0.0})
        assert unsure_signal(clip) < 0.1

    def test_narrow_margin_raises_uncertainty(self) -> None:
        wide = make_clip(confidence={"min_top1": 0.6, "mean_margin": 0.9, "detection_instability": 0.0})
        narrow = make_clip(confidence={"min_top1": 0.6, "mean_margin": 0.05, "detection_instability": 0.0})
        assert unsure_signal(narrow) > unsure_signal(wide)


class TestConflictClockGate:
    def test_trusted_below_threshold(self, config: SelectionConfig) -> None:
        clip = make_clip(disagreement=0.8, clock_sync_ms=4.0)
        assert conflict_signal(clip, config) == pytest.approx(0.8)

    def test_attenuated_in_the_grey_band(self, config: SelectionConfig) -> None:
        clip = make_clip(disagreement=0.8, clock_sync_ms=30.0)
        value = conflict_signal(clip, config)
        assert 0.0 < value < 0.8

    def test_disabled_above_threshold(self, config: SelectionConfig) -> None:
        # Sensors 200 ms apart appear to disagree on every frame. Trusting the
        # comparison would turn a timing fault into a fleet-wide false signal.
        clip = make_clip(disagreement=0.95, clock_sync_ms=200.0)
        assert conflict_signal(clip, config) is None

    def test_unknown_sync_withholds_the_signal(self, config: SelectionConfig) -> None:
        # Absence of evidence about synchronisation is not evidence of it.
        clip = make_clip(disagreement=0.95, clock_sync_ms=None)
        assert conflict_signal(clip, config) is None


class TestRare:
    def test_rarity_is_corpus_relative(self) -> None:
        corpus = [make_clip(f"c{i}", tags=["clear_day"]) for i in range(99)]
        corpus.append(make_clip("rare", tags=["dust"]))
        freq = scenario_frequencies(corpus)
        assert rare_signal(corpus[-1], freq) > rare_signal(corpus[0], freq)

    def test_untagged_clip_is_not_treated_as_exotic(self) -> None:
        # No tag means the taxonomy recognised nothing notable, not that the
        # clip is unusual.
        freq = scenario_frequencies([make_clip(tags=["clear_day"])])
        assert rare_signal(make_clip(tags=[]), freq) == 0.0


class TestQuality:
    def test_clean_clip_is_unpenalised(self, config: SelectionConfig) -> None:
        assert quality_multiplier(make_clip(), config) == 1.0

    def test_sensor_fault_dominates(self, config: SelectionConfig) -> None:
        clip = make_clip(quality={"blur": 0.1, "sensor_fault": True})
        assert quality_multiplier(clip, config) < 0.3

    def test_never_returns_zero(self, config: SelectionConfig) -> None:
        # A zero multiplier would make the score uninformative rather than low.
        clip = make_clip(quality={"blur": 1.0, "exposure_clipping": 1.0, "sensor_fault": True})
        assert quality_multiplier(clip, config) == config.quality_floor
