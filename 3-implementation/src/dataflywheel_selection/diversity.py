"""Stops one scene from eating the budget.

A single dusty afternoon produces hundreds of clips that are each genuinely
hard and nearly identical. Top-N by score buys that afternoon twenty times.

So every pick pushes its lookalikes down the list — harder the more alike they
are. They are deferred, not deleted; next cycle they come back.
"""

from __future__ import annotations

import numpy as np

# Brute-force cosine similarity, O(n^2). Fine to a few tens of thousands of
# clips; past that, swap in an ANN index behind the same interface.
_BRUTE_FORCE_LIMIT = 50_000


def normalise(embeddings: np.ndarray) -> np.ndarray:
    """Normalise rows, so a dot product is a cosine similarity."""
    if embeddings.size == 0:
        return embeddings
    norms = np.linalg.norm(embeddings, axis=1, keepdims=True)
    norms[norms == 0] = 1.0
    return embeddings / norms


def attenuation_factor(similarity: float, threshold: float, minimum: float) -> float:
    """How much to push a clip down, given how like a picked one it is.

    Graded, not on/off. A hard cutoff would either throw away useful variation
    just above it or let real duplicates through just below.
    """
    if similarity <= threshold:
        return 1.0
    if threshold >= 1.0:
        return minimum
    span = 1.0 - threshold
    overlap = min(1.0, (similarity - threshold) / span)
    return 1.0 - (1.0 - minimum) * overlap


class DiversityIndex:
    """Tracks how far each clip has been pushed down by earlier picks."""

    def __init__(
        self,
        embeddings: np.ndarray,
        threshold: float,
        min_attenuation: float,
    ) -> None:
        if embeddings.ndim != 2:
            raise ValueError("embeddings must be a 2-D array")
        if len(embeddings) > _BRUTE_FORCE_LIMIT:
            raise ValueError(
                f"{len(embeddings)} clips exceeds the brute-force limit of "
                f"{_BRUTE_FORCE_LIMIT}; wire in an ANN index for corpora this size"
            )
        self._matrix = normalise(embeddings.astype(np.float64, copy=True))
        self._threshold = threshold
        self._min_attenuation = min_attenuation
        self._attenuation = np.ones(len(embeddings), dtype=np.float64)

    @property
    def attenuation(self) -> np.ndarray:
        return self._attenuation

    def divisor(self, index: int) -> float:
        """The multiplier flipped, because "divided by 2.4" reads better."""
        factor = self._attenuation[index]
        return float("inf") if factor == 0 else round(1.0 / factor, 4)

    def mark_selected(self, index: int) -> None:
        """Push down everything that looks like the clip just picked."""
        if self._matrix.size == 0:
            return
        similarities = self._matrix @ self._matrix[index]
        similarities[index] = 0.0  # a clip does not attenuate itself
        affected = np.flatnonzero(similarities > self._threshold)
        for other in affected:
            self._attenuation[other] *= attenuation_factor(
                float(similarities[other]), self._threshold, self._min_attenuation
            )
