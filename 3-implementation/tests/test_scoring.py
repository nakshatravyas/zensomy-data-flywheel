"""Scoring, with emphasis on the cases a simpler design gets wrong."""

from __future__ import annotations

from dataflywheel_selection.config import SelectionConfig, SignalWeights
from dataflywheel_selection.scoring import score_clip
from dataflywheel_selection.signals import scenario_frequencies
from tests.conftest import make_clip


def _freq(clips):
    return scenario_frequencies(clips)


class TestConfidentError:
    """The failure mode no uncertainty-based method can detect."""

    def test_confident_and_wrong_outranks_merely_uncertain(self, config: SelectionConfig) -> None:
        # The model reports 96% confidence. It is wrong: the vehicle logged a
        # near-miss and the sensors contradict the model. Uncertainty sampling
        # would rank this clip near the bottom of the corpus.
        confident_error = make_clip(
            "confident_error",
            events=[{"type": "near_miss", "severity": 1.0}],
            confidence={"min_top1": 0.96, "mean_margin": 0.9, "detection_instability": 0.01},
            disagreement=0.85,
            clock_sync_ms=3.0,
        )
        merely_uncertain = make_clip(
            "uncertain",
            confidence={"min_top1": 0.45, "mean_margin": 0.2, "detection_instability": 0.3},
            disagreement=0.1,
            clock_sync_ms=3.0,
        )
        corpus = [confident_error, merely_uncertain]
        freq = _freq(corpus)

        a = score_clip(confident_error, config, freq)
        b = score_clip(merely_uncertain, config, freq)

        assert a.signals.unsure is not None and a.signals.unsure < 0.15, "model is confident"
        assert a.base_score > b.base_score
        assert any("DANGEROUS" in r for r in a.reasons)

    def test_uncertainty_alone_would_invert_the_ranking(self, config: SelectionConfig) -> None:
        """Proves the four-signal design is load-bearing, not decorative."""
        confident_error = make_clip(
            "ce",
            events=[{"type": "near_miss", "severity": 1.0}],
            confidence={"min_top1": 0.96, "mean_margin": 0.9, "detection_instability": 0.01},
            disagreement=0.85,
        )
        merely_uncertain = make_clip(
            "mu",
            confidence={"min_top1": 0.45, "mean_margin": 0.2, "detection_instability": 0.3},
            disagreement=0.1,
        )
        corpus = [confident_error, merely_uncertain]
        freq = _freq(corpus)

        uncertainty_only = config.model_copy(
            update={"weights": SignalWeights(wrong=0.0, unsure=1.0, conflict=0.0, rare=0.0)}
        )
        a = score_clip(confident_error, uncertainty_only, freq)
        b = score_clip(merely_uncertain, uncertainty_only, freq)
        assert a.base_score < b.base_score, "uncertainty alone misses the dangerous clip"


class TestQualityIsAMultiplier:
    def test_faulty_sensor_suppressed_despite_maximal_signals(self, config: SelectionConfig) -> None:
        # Every difficulty signal is at its maximum because the sensor is
        # broken. An additive penalty would be outvoted by four strong terms;
        # a multiplier cannot be.
        faulty = make_clip(
            "faulty",
            events=[{"type": "emergency_brake", "severity": 1.0}],
            confidence={"min_top1": 0.05, "mean_margin": 0.02, "detection_instability": 0.98},
            disagreement=0.97,
            tags=["mud_on_lens"],
            quality={"blur": 0.4, "sensor_fault": True},
        )
        genuine = make_clip(
            "genuine",
            events=[{"type": "emergency_brake", "severity": 1.0}],
            confidence={"min_top1": 0.5, "mean_margin": 0.2, "detection_instability": 0.3},
            disagreement=0.5,
            tags=["dust"],
        )
        freq = _freq([faulty, genuine])
        assert score_clip(faulty, config, freq).base_score < score_clip(genuine, config, freq).base_score


class TestRenormalisation:
    def test_cold_start_does_not_penalise_a_clip_for_a_missing_model(
        self, config: SelectionConfig
    ) -> None:
        # Identical clips; one simply has no model score available yet. Treating
        # the absent signal as zero would rank it below an equivalent clip that
        # merely had more subsystems reporting.
        with_model = make_clip(
            "with",
            events=[{"type": "disengagement", "severity": 1.0}],
            confidence={"min_top1": 0.5, "mean_margin": 0.5, "detection_instability": 0.0},
            disagreement=0.4,
        )
        without_model = make_clip(
            "without",
            events=[{"type": "disengagement", "severity": 1.0}],
            confidence=None,
            disagreement=0.4,
        )
        freq = _freq([with_model, without_model])
        cold = score_clip(without_model, config, freq)

        assert cold.signals.unsure is None
        assert cold.base_score > 0.0
        assert any("cold start" in r for r in cold.reasons)

    def test_scores_stay_within_range_when_signals_are_missing(
        self, config: SelectionConfig
    ) -> None:
        clip = make_clip("bare", confidence=None, disagreement=None, tags=[])
        result = score_clip(clip, config, {})
        assert 0.0 <= result.base_score <= 1.0


class TestExplainability:
    def test_every_selection_carries_its_justification(self, config: SelectionConfig) -> None:
        clip = make_clip(
            "x",
            events=[{"type": "disengagement", "severity": 1.0}],
            confidence={"min_top1": 0.3, "mean_margin": 0.1, "detection_instability": 0.5},
            disagreement=0.7,
            tags=["dust"],
        )
        reasons = score_clip(clip, config, _freq([clip])).reasons
        assert any("disengagement" in r for r in reasons)
        assert "the model was unsure" in reasons
        assert "camera and LiDAR disagreed" in reasons
