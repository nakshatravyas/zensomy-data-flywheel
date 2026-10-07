# Presentation

**Deliverable 4** — the 10–15 minute talk covering the Data Flywheel design.

`presentation.md` is a [Marp](https://marp.app) deck: plain Markdown, one slide per `---`.
Every slide carries speaker notes in an HTML comment at the end — that is the script, written to be read out loud.

Source material: `../1-TECHNICAL-DESIGN.md`, `../2-DESIGN-DOCUMENT.md`, `../3-implementation/`.
Every number and example in the deck comes from one of those three.

## Render the PDF

```bash
npx -y @marp-team/marp-cli@latest presentation.md --pdf --allow-local-files
```

Add `--pdf-notes` to put the speaker notes into the PDF.
`npx -y @marp-team/marp-cli@latest presentation.md -s` serves it live while editing.

## Timing budget

20 slides, 13 minutes of speaking, which leaves room inside the 15-minute limit.

| # | Slide | Time |
|---|---|---|
| 1 | Title | 0:20 |
| 2 | Two numbers decide the architecture | 1:00 |
| 3 | A pipeline runs and stops | 0:50 |
| 4 | The whole loop, one picture | 0:50 |
| 5 | The vehicle decides what leaves | 0:45 |
| 6 | Integrity and quality | 0:45 |
| 7 | Four signals | 0:50 |
| 8 | Scoring, diversity, the budget | 0:50 |
| 9 | Two structural choices in that score | 0:40 |
| 10 | The selection component is implemented | 0:45 |
| 11 | A dataset version is a manifest | 0:40 |
| 12 | Reproducibility: four pins | 0:35 |
| 13 | Evaluation gates per slice | 0:45 |
| 14 | The release unit is a bundle | 0:45 |
| 15 | The gate and the staged rollout | 0:45 |
| 16 | Cloud: managed by default | 0:40 |
| 17 | What breaks first is not the cloud | 0:35 |
| 18 | The three edges that close the loop | 0:55 |
| 19 | Five trade-offs, with the cost stated | 0:40 |
| 20 | Three claims this design makes | 0:25 |
| | **Total** | **13:00** |

Slides 2, 8 and 18 are the three that must land: the constraint, the worked ranking, and the closed loop.
If the clock runs short, 9 and 12 are the ones to compress.

## If asked to go deeper

| Question | Where the answer is |
|---|---|
| Full ranking example, all 8 clips | Technical Design §4 |
| All 47 trade-offs | Design Document §8 |
| The 12 stated assumptions | Design Document, *Assumptions* |
| Why each AWS service, and what was rejected | Design Document §5.1 |
| The code, its tests and example output | `../3-implementation/` |
