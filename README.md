# Data Flywheel for Autonomous Systems

Technical assessment — **Data Engineer, Autonomous Systems** · Zensomy Autonomous Technologies
**Nakshatra Vyas** · October 2026

A continuous loop that turns field data from off-road autonomous machines into measurably better
models, and sends the machines back out to collect what the models still get wrong.

📖 **Read the documents online: <https://nakshatravyas.github.io/zensomy-data-flywheel/>**

---

## The four deliverables

| # | Deliverable | Here |
|---|---|---|
| 1 | **Technical Design** — high-level architecture covering the complete flywheel | [`1-TECHNICAL-DESIGN.md`](1-TECHNICAL-DESIGN.md) |
| 2 | **Design Document** — the major decisions, the assumptions, and the trade-offs | [`2-DESIGN-DOCUMENT.md`](2-DESIGN-DOCUMENT.md) |
| 3 | **Practical Implementation** — working code for the data-selection component | [`3-implementation/`](3-implementation/) |
| 4 | **Presentation** — 10–15 minutes | [`4-presentation/`](4-presentation/) |

Deliverable 2 opens with a requirement coverage matrix mapping every bullet in the brief to the
section that answers it.

## Running the implementation

```bash
cd 3-implementation
docker compose up --build
```

That is the whole setup. Full instructions, including the local path for running the tests, are in
[`3-implementation/README.md`](3-implementation/README.md).

## Building the documentation site

```bash
cd .site
python3 -m venv .venv && .venv/bin/pip install -r requirements.txt
./sync.sh                      # copy the two documents in, rewriting cross-references
.venv/bin/mkdocs serve         # preview on localhost:8000
.venv/bin/mkdocs gh-deploy     # publish to GitHub Pages
```

The site renders the same Markdown that is submitted — it is a view of these files, not a separate
copy that can drift.
