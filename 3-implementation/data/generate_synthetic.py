#!/usr/bin/env python3
"""Generate a synthetic catalog export for demonstration and testing.

Real sensor data cannot be shipped with this submission, so the corpus is
synthesised with the structure the selection stage actually depends on:

* an overwhelming majority of ordinary clips, matching the real problem —
  most operational footage is a machine driving in a straight line
* a small number of logged failure events
* clusters of near-identical clips, so diversity attenuation has something
  to do (one dusty afternoon produces hundreds of similar frames)
* a vehicle with a faulty sensor, which scores highly on every difficulty
  signal and must be suppressed by the quality multiplier
* confident errors — the model certain, the sensors contradicting it
* a handful of clips with unusable clock synchronisation, so the CONFLICT
  gate is exercised

Deterministic: the same seed always produces the same corpus.

    python data/generate_synthetic.py --count 600 --seed 7 --out data/example_input.jsonl
"""

from __future__ import annotations

import argparse
import json
import math
import random
from pathlib import Path

DIM = 8
VEHICLES = ["veh01", "veh02", "veh03", "veh04", "veh05"]
SITES = ["green_valley", "ridgefield", "north_quarry", "west_slope"]
COMMON = ["clear_day", "flat_terrain", "open_field"]
RARE = ["dust", "low_sun", "wet_ground", "steep_grade", "dense_canopy", "night", "mud_on_lens"]


def unit(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vector)) or 1.0
    return [round(v / norm, 6) for v in vector]


def near(centre: list[float], rng: random.Random, jitter: float) -> list[float]:
    return unit([v + rng.gauss(0.0, jitter) for v in centre])


def generate(count: int, seed: int) -> list[dict]:
    rng = random.Random(seed)
    clusters = [unit([rng.gauss(0, 1) for _ in range(DIM)]) for _ in range(12)]
    dust_cluster = clusters[0]
    clips: list[dict] = []

    for i in range(count):
        vehicle = rng.choice(VEHICLES)
        hour = 6 + (i % 14)
        clip_id = f"{vehicle}_2026091{i % 9}T{hour:02d}{i % 60:02d}{i % 60:02d}_{i:04d}"

        # veh05 has a degraded sensor for part of the corpus. It will look
        # maximally interesting on every difficulty signal and must not be
        # allowed to consume the budget.
        faulty = vehicle == "veh05" and i % 3 == 0

        # One sustained dusty afternoon: many near-identical, genuinely
        # difficult clips. Pure ranking would spend the budget here.
        in_dust_run = 120 <= i < 190

        roll = rng.random()
        events: list[dict] = []
        tags = rng.sample(COMMON, k=rng.randint(1, 2))

        if in_dust_run:
            embedding = near(dust_cluster, rng, 0.03)
            tags = ["dust"] + rng.sample(COMMON, k=1)
            if rng.random() < 0.18:
                events.append({"type": "emergency_brake", "severity": 0.9})
            confidence = {
                "min_top1": round(rng.uniform(0.30, 0.55), 3),
                "mean_margin": round(rng.uniform(0.05, 0.25), 3),
                "detection_instability": round(rng.uniform(0.2, 0.5), 3),
            }
            disagreement = round(rng.uniform(0.25, 0.55), 3)

        elif roll < 0.03:
            # Logged failure — the strongest evidence in the system.
            embedding = near(rng.choice(clusters), rng, 0.25)
            tags = rng.sample(RARE, k=rng.randint(1, 2))
            events.append({"type": rng.choice(["disengagement", "emergency_brake", "near_miss"]), "severity": 1.0})
            confidence = {
                "min_top1": round(rng.uniform(0.25, 0.60), 3),
                "mean_margin": round(rng.uniform(0.05, 0.30), 3),
                "detection_instability": round(rng.uniform(0.2, 0.6), 3),
            }
            disagreement = round(rng.uniform(0.3, 0.7), 3)

        elif roll < 0.055:
            # Confident error: the model is certain and the sensors contradict
            # it. Uncertainty sampling cannot see this clip at all.
            embedding = near(rng.choice(clusters), rng, 0.3)
            tags = rng.sample(RARE, k=1)
            events.append({"type": "near_miss", "severity": 0.95})
            confidence = {"min_top1": 0.96, "mean_margin": 0.88, "detection_instability": 0.02}
            disagreement = round(rng.uniform(0.70, 0.92), 3)

        elif roll < 0.12:
            # Rare scenario, nothing went wrong — valuable for coverage.
            embedding = near(rng.choice(clusters), rng, 0.3)
            tags = rng.sample(RARE, k=rng.randint(1, 2))
            confidence = {
                "min_top1": round(rng.uniform(0.45, 0.75), 3),
                "mean_margin": round(rng.uniform(0.15, 0.45), 3),
                "detection_instability": round(rng.uniform(0.05, 0.3), 3),
            }
            disagreement = round(rng.uniform(0.05, 0.3), 3)

        else:
            # The overwhelming majority: ordinary operation the stack handles.
            embedding = near(rng.choice(clusters), rng, 0.35)
            confidence = {
                "min_top1": round(rng.uniform(0.82, 0.99), 3),
                "mean_margin": round(rng.uniform(0.55, 0.95), 3),
                "detection_instability": round(rng.uniform(0.0, 0.08), 3),
            }
            disagreement = round(rng.uniform(0.0, 0.15), 3)

        # A few vehicles drift out of clock synchronisation, which must disable
        # the cross-sensor signal rather than producing fleet-wide false alarms.
        if vehicle == "veh04" and i % 11 == 0:
            clock_ms = round(rng.uniform(60.0, 140.0), 1)
        else:
            clock_ms = round(rng.uniform(0.5, 12.0), 1)

        quality = {
            "blur": round(rng.uniform(0.0, 0.08), 3),
            "exposure_clipping": round(rng.uniform(0.0, 0.06), 3),
            "dropped_frame_rate": round(rng.uniform(0.0, 0.03), 3),
            "sensor_fault": faulty,
        }
        if faulty:
            quality["blur"] = round(rng.uniform(0.25, 0.45), 3)
            confidence = {"min_top1": 0.12, "mean_margin": 0.05, "detection_instability": 0.92}
            disagreement = 0.94
            tags = ["mud_on_lens"] + tags[:1]

        clips.append(
            {
                "clip_id": clip_id,
                "vehicle_id": vehicle,
                "session_id": f"S-{(i // 25):04d}",
                "site": SITES[(i // 60) % len(SITES)],
                "start_time": f"2026-09-1{i % 9}T{hour:02d}:{i % 60:02d}:{i % 60:02d}Z",
                "duration_s": 10.0,
                "events": events,
                "model_confidence": confidence,
                "cross_sensor": {"disagreement_rate": disagreement},
                "clock_sync_ms": clock_ms,
                "scenario_tags": sorted(set(tags)),
                "quality": quality,
                "embedding": embedding,
                "already_labelled": (i % 97 == 0),
            }
        )

    return clips


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=600)
    parser.add_argument("--seed", type=int, default=7)
    parser.add_argument("--out", default="data/example_input.jsonl")
    parser.add_argument(
        "--cold-start",
        action="store_true",
        help="Strip model scores, as before any model has been trained.",
    )
    args = parser.parse_args()

    path = Path(args.out)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        for clip in generate(args.count, args.seed):
            if args.cold_start:
                clip.pop("model_confidence", None)
            handle.write(json.dumps(clip, sort_keys=True) + "\n")
    print(f"wrote {args.count} clips to {path}")


if __name__ == "__main__":
    main()
