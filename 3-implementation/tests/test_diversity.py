"""Diversity attenuation — the mechanism that stops ranking from saturating."""

from __future__ import annotations

import numpy as np
import pytest

from dataflywheel_selection.diversity import DiversityIndex, attenuation_factor, normalise


class TestAttenuationFactor:
    def test_below_threshold_is_untouched(self) -> None:
        assert attenuation_factor(0.5, threshold=0.85, minimum=0.3) == 1.0

    def test_identical_is_fully_attenuated(self) -> None:
        assert attenuation_factor(1.0, threshold=0.85, minimum=0.3) == pytest.approx(0.3)

    def test_graded_in_between(self) -> None:
        # A binary rule would either discard useful variation just above the
        # threshold or fail to suppress true duplicates just below it.
        mild = attenuation_factor(0.87, threshold=0.85, minimum=0.3)
        strong = attenuation_factor(0.99, threshold=0.85, minimum=0.3)
        assert 0.3 < strong < mild < 1.0

    def test_monotonic_in_similarity(self) -> None:
        values = [attenuation_factor(s, 0.85, 0.3) for s in (0.86, 0.90, 0.95, 1.00)]
        assert values == sorted(values, reverse=True)


class TestDiversityIndex:
    def test_selection_attenuates_neighbours_only(self) -> None:
        near_a = [1.0, 0.0]
        near_b = [0.99, 0.14]
        far = [0.0, 1.0]
        index = DiversityIndex(np.array([near_a, near_b, far]), threshold=0.85, min_attenuation=0.3)

        index.mark_selected(0)

        assert index.attenuation[1] < 1.0, "near neighbour attenuated"
        assert index.attenuation[2] == 1.0, "unrelated clip untouched"

    def test_a_clip_does_not_attenuate_itself(self) -> None:
        index = DiversityIndex(np.array([[1.0, 0.0]]), threshold=0.85, min_attenuation=0.3)
        index.mark_selected(0)
        assert index.attenuation[0] == 1.0

    def test_repeated_selections_compound(self) -> None:
        vectors = np.array([[1.0, 0.0], [0.999, 0.045], [0.998, 0.063]])
        index = DiversityIndex(vectors, threshold=0.85, min_attenuation=0.3)
        index.mark_selected(0)
        first = index.attenuation[2]
        index.mark_selected(1)
        assert index.attenuation[2] < first

    def test_divisor_is_the_reciprocal(self) -> None:
        index = DiversityIndex(np.array([[1.0, 0.0], [1.0, 0.0]]), threshold=0.85, min_attenuation=0.5)
        index.mark_selected(0)
        assert index.divisor(1) == pytest.approx(2.0, rel=1e-3)

    def test_zero_vector_is_similar_to_nothing(self) -> None:
        # A clip with no embedding must never be assumed to duplicate something
        # already selected.
        index = DiversityIndex(np.array([[1.0, 0.0], [0.0, 0.0]]), threshold=0.85, min_attenuation=0.3)
        index.mark_selected(0)
        assert index.attenuation[1] == 1.0

    def test_refuses_corpora_beyond_the_brute_force_limit(self) -> None:
        # Fails loudly rather than silently taking minutes per run.
        with pytest.raises(ValueError, match="ANN index"):
            DiversityIndex(np.zeros((50_001, 2)), threshold=0.85, min_attenuation=0.3)


class TestNormalise:
    def test_rows_become_unit_length(self) -> None:
        out = normalise(np.array([[3.0, 4.0], [0.0, 2.0]]))
        assert np.allclose(np.linalg.norm(out, axis=1), 1.0)

    def test_zero_row_survives(self) -> None:
        out = normalise(np.array([[0.0, 0.0]]))
        assert np.isfinite(out).all()
