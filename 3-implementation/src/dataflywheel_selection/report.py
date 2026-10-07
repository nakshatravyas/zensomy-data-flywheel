"""The summary written at the end of every run.

For the person approving the spend, not for the next program. Plain language
on purpose, and its job is to make every reduction visible: what was dropped,
which limits bound, where the budget went.
"""

from __future__ import annotations

from collections import Counter

from .models import SelectionResult


def render_report(result: SelectionResult, input_digest: str) -> str:
    funnel = result.funnel
    buckets = Counter(clip.bucket for clip in result.selected)
    out: list[str] = []
    add = out.append

    # ---- headline ---------------------------------------------------------
    add("# Which clips to send for labelling\n")
    add(
        f"We looked at **{funnel.input_clips} clips** and picked "
        f"**{funnel.selected}** of them.\n"
    )
    add(
        f"We can label about 1% of what we record. That is "
        f"{result.budget_seconds / 3600:.2f} hours here, and we used "
        f"{result.selected_seconds / 3600:.2f} of it "
        f"({_pct(result.selected_seconds, result.budget_seconds)}).\n"
    )
    add(f"*Run seed `{result.config.get('seed')}` · input file `{input_digest[:16]}…`*\n")

    # ---- funnel -----------------------------------------------------------
    add("## What happened to all the clips\n")
    add("| | Clips |")
    add("|---|---:|")
    add(f"| Came in | {funnel.input_clips} |")
    add(f"| Skipped — we already paid to label these | {funnel.dropped_already_labelled} |")
    add(f"| Skipped — too damaged to be useful | {funnel.dropped_low_quality} |")
    add(f"| Ranked | {funnel.scored} |")
    add(f"| **Picked** | **{funnel.selected}** |")
    add("")
    add("Nothing is dropped without a reason. The full list is in `dropped.jsonl`.\n")

    if funnel.must_take_deferred_over_share or funnel.vehicles_at_cap:
        add("### Limits that came into play\n")
        add("Stated openly — a limit nobody mentions looks like full coverage.\n")
        if funnel.must_take_deferred_over_share:
            add(
                f"- **{funnel.must_take_deferred_over_share} clips where the vehicle logged a "
                "problem did not fit.** These are the most valuable clips we have, and there "
                "were more of them than this round could pay for. They go to the front of the "
                "queue next time."
            )
        if funnel.vehicles_at_cap:
            n = funnel.vehicles_at_cap
            add(
                f"- **{n} machine{'' if n == 1 else 's'} hit "
                f"{'its' if n == 1 else 'their'} individual limit**, which left "
                f"{funnel.budget_unspendable_s:.0f} seconds unspent. No single machine is "
                "allowed to take the whole budget. Nothing valuable was thrown away."
            )
        add("")

    # ---- buckets ----------------------------------------------------------
    add("## Why each clip was picked\n")
    add("| Reason | Clips | What this group is for |")
    add("|---|---:|---|")
    add(
        f"| The vehicle itself logged a problem | {buckets.get('must_take', 0)} | "
        "Someone took over, braked hard, or nearly hit something. The strongest evidence "
        "we have that the machine got it wrong. Always included. |"
    )
    add(
        f"| Highest scoring, duplicates removed | {buckets.get('scored', 0)} | "
        "Difficult moments, ranked. A clip that looks almost identical to one already "
        "picked is pushed down, so we buy variety instead of the same scene twice. |"
    )
    add(
        f"| Picked at random | {buckets.get('random', 0)} | "
        "Deliberately chosen without looking at the score. If every labelled clip were one "
        "the model struggled with, we could never measure how it does on normal driving — "
        "and this is the only way we find problems we weren't looking for. |"
    )
    add("")

    # ---- signal availability ----------------------------------------------
    add("## What we were able to check\n")
    add(
        "Not every check is possible on every clip. When one is missing, the remaining "
        "checks are reweighted — a check we could not run is never counted as a check that "
        "came back clean.\n"
    )
    add("| Check | What it looks for | Clips we could run it on |")
    add("|---|---|---:|")
    labels = {
        "wrong": "Did the vehicle log a problem?",
        "unsure": "Was the model unsure of itself?",
        "conflict": "Did the camera and LiDAR disagree?",
        "rare": "Is this an uncommon situation?",
    }
    for name, description in labels.items():
        add(f"| {name.upper()} | {description} | {result.signal_availability.get(name, 0)} |")
    add("")

    # ---- per vehicle -------------------------------------------------------
    add("## Which machines the work came from\n")
    add("No single machine is allowed to dominate — a dirty camera lens is not a discovery.\n")
    add("| Machine | Seconds | Share of what we can label |")
    add("|---|---:|---:|")
    for vehicle, seconds in sorted(result.per_vehicle_seconds.items(), key=lambda kv: -kv[1]):
        add(f"| {vehicle} | {seconds:.0f} | {_pct(seconds, result.budget_seconds)} |")
    add("")

    # ---- coverage ----------------------------------------------------------
    add("## Conditions this selection covers\n")
    add("A selection that is all one condition teaches the model one thing.\n")
    add("| Condition | Clips |")
    add("|---|---:|")
    for tag, count in sorted(result.scenario_coverage.items(), key=lambda kv: (-kv[1], kv[0])):
        add(f"| {tag} | {count} |")
    add("")

    # ---- top picks ---------------------------------------------------------
    add("## The top 15 picks, and why\n")
    add(
        "*Score* is how valuable the clip looked. *Repeat* is how much it was marked down "
        "for resembling something already picked — 1.00 means it was unlike anything else.\n"
    )
    add("| # | Clip | Why it was in | Score | Repeat | Final | Reasons |")
    add("|---:|---|---|---:|---:|---:|---|")
    group = {"must_take": "vehicle logged a problem", "scored": "scored high", "random": "random"}
    for clip in result.selected[:15]:
        why = "; ".join(clip.reasons) if clip.reasons else "—"
        add(
            f"| {clip.rank} | `{clip.clip_id}` | {group.get(clip.bucket or '', '—')} | "
            f"{clip.base_score:.3f} | ÷{clip.similarity_divisor:.2f} | "
            f"{clip.effective_score:.3f} | {why} |"
        )
    add("")

    add("---\n")
    add(
        "**Files alongside this one** — `selected.jsonl` every pick with its full working, "
        "`dropped.jsonl` everything skipped and why, `run_manifest.json` the exact settings "
        "and a fingerprint of the input, so this run can be reproduced.\n"
    )

    return "\n".join(out)


def _pct(part: float, whole: float) -> str:
    return f"{(100.0 * part / whole):.1f}%" if whole else "—"
