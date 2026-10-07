"""Command line.

    select-data --input data/example_input.jsonl --out data/example_output
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .config import SelectionConfig
from .io import InputError, file_digest, read_clips, write_result
from .pipeline import run_selection


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="select-data",
        description="Select the clips most worth annotating, within a fixed budget.",
    )
    parser.add_argument("--input", "-i", required=True, help="Catalog export, newline-delimited JSON.")
    parser.add_argument("--out", "-o", required=True, help="Output directory.")
    parser.add_argument("--quiet", "-q", action="store_true", help="Suppress the stdout summary.")
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    config = SelectionConfig()

    try:
        clips = read_clips(args.input)
    except InputError as exc:
        # Fail loudly. Quietly skipping part of the corpus would still produce
        # output that looks fine.
        print(f"error: {exc}", file=sys.stderr)
        return 2

    result = run_selection(clips, config)
    paths = write_result(result, args.out, file_digest(args.input))

    if not args.quiet:
        _summarise(result, paths)
    return 0


def _summarise(result, paths: dict[str, Path]) -> None:
    f = result.funnel
    print(f"input           {f.input_clips} clips")
    print(f"dropped         {f.dropped_already_labelled} already labelled, {f.dropped_low_quality} low quality")
    print(f"scored          {f.scored}")
    print(
        f"selected        {f.selected} clips "
        f"({result.selected_seconds / 3600:.2f} h of {result.budget_seconds / 3600:.2f} h we can label)"
    )
    if f.must_take_deferred_over_share:
        print(f"  deferred      {f.must_take_deferred_over_share} must-take clips over bucket share")
    if f.vehicles_at_cap:
        print(
            f"  capped        {f.vehicles_at_cap} vehicle(s) at the per-vehicle limit "
            f"({f.budget_unspendable_s:.0f} s unspendable)"
        )
    print(f"report          {paths['report']}")


if __name__ == "__main__":
    raise SystemExit(main())
