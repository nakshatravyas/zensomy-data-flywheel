"""Reading the input file and writing the four output files.

The input comes from another system, so it is checked rather than trusted. A
bad line stops the run with its line number — a selection that quietly skipped
part of its corpus would still look fine.
"""

from __future__ import annotations

import hashlib
import json
from collections.abc import Iterator
from pathlib import Path

import numpy as np
from pydantic import ValidationError

from .models import Clip, SelectionResult
from .report import render_report


class InputError(ValueError):
    """The input file cannot be trusted."""


def read_clips(path: str | Path) -> list[Clip]:
    """Read the JSONL input, validating as we go."""
    path = Path(path)
    if not path.exists():
        raise InputError(f"input file not found: {path}")

    clips: list[Clip] = []
    seen: set[str] = set()

    for line_number, line in _iter_lines(path):
        try:
            record = json.loads(line)
        except json.JSONDecodeError as exc:
            raise InputError(f"{path}:{line_number}: invalid JSON — {exc.msg}") from exc
        try:
            clip = Clip.model_validate(record)
        except ValidationError as exc:
            first = exc.errors()[0]
            field = ".".join(str(p) for p in first["loc"]) or "<record>"
            raise InputError(f"{path}:{line_number}: {field}: {first['msg']}") from exc

        if clip.clip_id in seen:
            raise InputError(f"{path}:{line_number}: duplicate clip_id {clip.clip_id!r}")
        seen.add(clip.clip_id)
        clips.append(clip)

    if not clips:
        raise InputError(f"{path}: no records")
    return clips


def embedding_matrix(clips: list[Clip]) -> np.ndarray:
    """Stack the embeddings, checking they are all the same size.

    No embedding means a zero vector: similar to nothing, so it never gets
    pushed down and never pushes anything else down. We should not assume a
    clip we cannot compare is a duplicate.
    """
    dims = {len(c.embedding) for c in clips if c.embedding}
    if len(dims) > 1:
        raise InputError(f"inconsistent embedding dimensions in input: {sorted(dims)}")
    dim = dims.pop() if dims else 1

    matrix = np.zeros((len(clips), dim), dtype=np.float64)
    for row, clip in enumerate(clips):
        if clip.embedding:
            matrix[row] = clip.embedding
    return matrix


def file_digest(path: str | Path) -> str:
    """SHA-256 of the input, written into the manifest.

    So "this came from exactly that corpus" is checkable, not just claimed.
    """
    digest = hashlib.sha256()
    with open(path, "rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def write_result(result: SelectionResult, out_dir: str | Path, input_digest: str) -> dict[str, Path]:
    """Write the four output files."""
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)

    selected_path = out / "selected.jsonl"
    with open(selected_path, "w", encoding="utf-8") as handle:
        for clip in result.selected:
            handle.write(json.dumps(clip.model_dump(), sort_keys=True) + "\n")

    manifest_path = out / "run_manifest.json"
    manifest = {
        "input_sha256": input_digest,
        "config": result.config,
        "funnel": result.funnel.model_dump(),
        "budget_seconds": result.budget_seconds,
        "selected_seconds": result.selected_seconds,
        "signal_availability": result.signal_availability,
        "per_vehicle_seconds": result.per_vehicle_seconds,
        "scenario_coverage": result.scenario_coverage,
    }
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    dropped_path = out / "dropped.jsonl"
    with open(dropped_path, "w", encoding="utf-8") as handle:
        for item in result.dropped:
            handle.write(json.dumps(item.model_dump(), sort_keys=True) + "\n")

    report_path = out / "report.md"
    report_path.write_text(render_report(result, input_digest), encoding="utf-8")

    return {
        "selected": selected_path,
        "manifest": manifest_path,
        "dropped": dropped_path,
        "report": report_path,
    }


def _iter_lines(path: Path) -> Iterator[tuple[int, str]]:
    with open(path, "r", encoding="utf-8") as handle:
        for number, raw in enumerate(handle, start=1):
            line = raw.strip()
            if line:
                yield number, line
