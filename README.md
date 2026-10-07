# Data Flywheel for Autonomous Systems

Technical assessment - **Data Engineer, Autonomous Systems** · Zensomy Autonomous Technologies
**Nakshatra Vyas** · October 2026

A continuous loop that turns field data from off-road autonomous machines into measurably better
models, and sends the machines back out to collect what the models still get wrong.

📖 **Read the documents online: <https://nakshatravyas.github.io/zensomy-data-flywheel/>**

---

## The four deliverables

| # | Deliverable | Here |
|---|---|---|
| 1 | **Technical Design** - high-level architecture covering the complete flywheel | [`1-technical-design/`](1-technical-design/) |
| 2 | **Design Document** - the major decisions, the assumptions, and the trade-offs | [`2-design-document/`](2-design-document/) |
| 3 | **Practical Implementation** - working code for the data-selection component | [`3-implementation/`](3-implementation/) |
| 4 | **Presentation** - 10-15 minutes | [`4-presentation/`](4-presentation/) |

---

## Running the implementation

### 1. Get the code

Either clone the repository:

```bash
git clone https://github.com/nakshatravyas/zensomy-data-flywheel.git
cd zensomy-data-flywheel
```

Or download it as a ZIP from the green **Code** button above, unzip it, and open a terminal in
the unzipped folder.

### 2. Run it

```bash
cd 3-implementation
docker compose up --build
```

That is the whole setup. Docker builds the image, runs the selection pipeline over the example
corpus, and writes the results to `3-implementation/output/`.

After the first build, `docker compose up` on its own is enough.

### 3. Read the output

| File | What it holds |
|---|---|
| `output/report.md` | A plain-language explanation of what was picked and why |
| `output/selected.jsonl` | Every selected clip with its full scoring breakdown |
| `output/dropped.jsonl` | Everything that was skipped, and the reason |
| `output/run_manifest.json` | The exact settings and a fingerprint of the input, so the run can be reproduced |

Running the tests, and the local path without Docker, are covered in
[`3-implementation/README.md`](3-implementation/README.md).
