"""Configuration validation — bad numbers are rejected before a run starts."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from dataflywheel_selection.config import SelectionConfig, SignalWeights


class TestValidation:
    def test_budget_shares_must_sum_to_one(self) -> None:
        with pytest.raises(ValidationError, match="sum to 1.0"):
            SelectionConfig(must_take_share=0.5, scored_share=0.5, random_share=0.5)

    def test_clock_gate_thresholds_must_be_ordered(self) -> None:
        with pytest.raises(ValidationError, match="must exceed"):
            SelectionConfig(clock_sync_trust_ms=60.0, clock_sync_disable_ms=10.0)

    def test_all_zero_weights_are_rejected(self) -> None:
        with pytest.raises(ValidationError, match="positive"):
            SignalWeights(wrong=0.0, unsure=0.0, conflict=0.0, rare=0.0)

    def test_unknown_keys_are_rejected(self) -> None:
        # A typo in a config file must fail the run, not be ignored.
        with pytest.raises(ValidationError):
            SelectionConfig.model_validate({"budget_hours": 1.0, "budget_hrs": 2.0})

    def test_negative_budget_is_rejected(self) -> None:
        with pytest.raises(ValidationError):
            SelectionConfig(budget_hours=-1.0)


class TestRoundTrip:
    def test_config_survives_a_file_round_trip(self, tmp_path) -> None:
        original = SelectionConfig(budget_hours=12.5, seed=99)
        path = tmp_path / "config.json"
        path.write_text(json.dumps(original.model_dump(mode="json")), encoding="utf-8")
        assert SelectionConfig.from_file(path) == original

    def test_the_limit_defaults_to_one_percent_of_the_pool(self) -> None:
        """Nothing to configure: we label about 1% of what we record."""
        assert SelectionConfig().budget_seconds(360_000.0) == 3_600.0
