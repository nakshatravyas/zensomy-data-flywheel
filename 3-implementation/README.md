# Data Selection Pipeline

**Deliverable 3** - working code for one part of the Data Flywheel.

The problem: we record far more than we can label. A person has to draw boxes on every object in every frame, and that is the expensive step. **We can label about 1% of what we record** - 100 hours out of 10,000.

This program decides which 1%.

> Design behind it: `../1-TECHNICAL-DESIGN.md` §4

---

## Run it - Docker

```bash
cd 3-implementation
docker compose up --build     # first time
docker compose up             # after that
```

Nothing else to install.

Output lands in **`./output/`**:

| File | |
|---|---|
| `report.md` | Plain summary - **read this first** |
| `selected.jsonl` | Every pick, and why |
| `dropped.jsonl` | Everything skipped, and why |
| `run_manifest.json` | Settings used, plus a fingerprint of the input |

## Run it locally

Needed for the tests. Python 3.10+.

```bash
make install      # .venv + dependencies
make test         # 73 tests
make run          # a selection
```

---

## What it does

```
6000 clips in
   │
   ├─ drop what we already labelled            62
   ├─ drop what is too damaged to use         205
   │
   ▼  score what is left                     5733
   │
   │   WRONG     did the vehicle log a failure?
   │   UNSURE    was the model not confident?
   │   CONFLICT  did camera and LiDAR disagree?
   │   RARE      is this an uncommon situation?
   │
   │   × quality   ÷ how much it looks like something already picked
   │
   ▼  spend what we can label
   │
   │   20%  the vehicle logged a failure - always taken
   │   70%  best score first, lookalikes pushed down
   │   10%  picked at random, on purpose
   │
   ▼
  55 clips out
```

**Why four signals and not just uncertainty.** The dangerous case is the model being **confident and wrong** - 96% sure, and the LiDAR says there is something there. Uncertainty sampling cannot see that clip at all. `WRONG` and `CONFLICT` can.

**Why the random 10%.** If every labelled clip is one the model struggled with, we can never measure how it does on normal driving. It is also the only way we find problems no signal was built to look for.

**Why lookalikes get pushed down.** One dusty afternoon produces hundreds of clips that are each genuinely hard and nearly identical. Pure top-N buys that afternoon twenty times.

---

## Design decisions

**Quality multiplies, it does not subtract.** A broken sensor looks maximally interesting - high uncertainty *and* high disagreement at once. Subtracting a penalty gets outvoted by four strong signals. Multiplying cannot be.

**A missing signal is not a zero signal.** If there is no model yet, or the sensor clocks have drifted too far to trust, that signal returns nothing and the rest are reweighted. Scoring it as zero would push the clip down just because fewer subsystems were reporting.

**Cross-sensor disagreement is gated on clock sync.** 200 ms of drift is 0.56 m at 10 km/h - enough to make working sensors look like they disagree on every frame. Without the gate, a timing fault becomes a fleet-wide false alarm.

**No machine may take more than its share.** One tractor with a dirty lens would otherwise eat everything. A machine that keeps hitting the cap is telling us it needs maintenance.

**Nothing is dropped silently.** Every skipped clip has a recorded reason, every limit that bound is named in the report, and a test asserts `input = dropped + scored`. A selection stage that only reports its output looks identical to one that is quietly broken.

**Same input, same output.** Ties break on clip ID, input order does not matter, and the manifest records a hash of the input file.

**Input is not trusted.** It comes from another system. A bad line fails the run with its line number and the offending field.

---

## Tests

```bash
make test
```

73 tests. Each name is a promise the design makes:

| Test | What it defends |
|---|---|
| `test_uncertainty_alone_would_invert_the_ranking` | Four signals are necessary, not decorative - uncertainty alone ranks the dangerous clip *last* |
| `test_faulty_sensor_suppressed_despite_maximal_signals` | A broken sensor cannot buy attention |
| `test_disabled_above_threshold` | A clock fault does not become a fleet-wide false signal |
| `test_cold_start_does_not_penalise_a_clip_for_a_missing_model` | Missing ≠ zero |
| `test_one_cluster_cannot_consume_the_budget` | 150 near-duplicates do not crowd out 10 different scenes |
| `test_logged_failures_are_never_crowded_out` | A disengagement is always picked |
| `test_every_input_clip_is_accounted_for` | Nothing vanishes |
| `test_a_dusty_lens_is_kept_not_dropped` | Dust is the job, not a defect |
| `test_runs_with_no_model_scores_at_all` | Works before any model exists |

---

## Input format

One JSON object per line. `data/example_input.jsonl` holds 6000 synthetic clips, committed so it runs with no setup.

```json
{
  "clip_id": "veh03_20260914T081233_0417",
  "vehicle_id": "veh03",
  "session_id": "S-0412",
  "duration_s": 10.0,
  "events": [{"type": "disengagement", "severity": 1.0}],
  "model_confidence": {"min_top1": 0.41, "mean_margin": 0.12, "detection_instability": 0.33},
  "cross_sensor": {"disagreement_rate": 0.44},
  "clock_sync_ms": 4.2,
  "scenario_tags": ["dust", "low_sun"],
  "quality": {"blur": 0.08, "exposure_clipping": 0.03, "dropped_frame_rate": 0.01, "sensor_fault": false},
  "embedding": [0.39, 0.23, 0.15, 0.34, -0.66, 0.16, 0.41, 0.16],
  "already_labelled": false
}
```

`model_confidence` and `cross_sensor` are optional - leaving them out is the cold-start case, and it still works.

## Output format

```json
{
  "clip_id": "veh01_20260918T092929_0269",
  "rank": 1,
  "bucket": "must_take",
  "signals": {"wrong": 1.0, "unsure": 0.579, "conflict": 0.563, "rare": 0.983},
  "quality_multiplier": 0.975,
  "base_score": 0.764,
  "similarity_divisor": 1.0,
  "reasons": ["the vehicle logged: disengagement", "camera and LiDAR disagreed", "an uncommon situation"]
}
```

Every pick carries its reasoning, so anyone can ask why we paid for a clip.

---

## Layout

```
├── Dockerfile              two stages: build, then the image that runs
├── docker-compose.yml      docker compose up --build
├── Makefile                install · test · run · clean
├── src/dataflywheel_selection/
│   ├── config.py           the numbers
│   ├── models.py           input and output shapes
│   ├── signals.py          the four signals, and quality
│   ├── scoring.py          combining them
│   ├── diversity.py        pushing lookalikes down
│   ├── budget.py           the three groups, and the per-machine cap
│   ├── pipeline.py         filter → score → pick
│   ├── io.py               reading input, writing the four files
│   ├── report.py           the summary, written every run
│   └── cli.py              command line
├── tests/                  73 tests
└── data/
    ├── example_input.jsonl 6000 clips
    ├── cold_start.jsonl    same clips, no model scores
    └── generate_synthetic.py
```

Two dependencies: **numpy**, **pydantic**.

---

## Left out on purpose

| Not built | Why | When to add |
|---|---|---|
| ANN index (FAISS) | Brute force is fine to tens of thousands of clips, and it raises an error past that instead of crawling | When a cycle's pool outgrows it |
| Real embedding model | Embeddings come from a GPU job upstream; they are an input here | Already in the architecture |
| Storage adapters | The contract is clips in, picks out. Storage belongs to whatever calls it | When wired into Airflow |
| Learned ranker | No history yet of which picks actually improved a model | After several cycles |

Each is an interface that exists, not a hole.
