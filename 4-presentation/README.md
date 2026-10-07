# Presentation

**Deliverable 4** - the 10–15 minute talk covering the Data Flywheel design.

`presentation.md` is a [Marp](https://marp.app) deck: plain Markdown, one slide per `---`.
Every slide carries speaker notes in an HTML comment at the end - that is the script, written to be read out loud.

Source material: `../1-TECHNICAL-DESIGN.md`, `../2-DESIGN-DOCUMENT.md`, `../3-implementation/`.
Every number and example in the deck comes from one of those three.

## Render the PDF

```bash
npx -y @marp-team/marp-cli@latest presentation.md --pdf --allow-local-files
```

Add `--pdf-notes` to put the speaker notes into the PDF.
`npx -y @marp-team/marp-cli@latest presentation.md -s` serves it live while editing.

## Timing budget

16 slides, 12 minutes of speaking, which leaves room inside the 15-minute limit.

| # | Slide | Time |
|---|---|---|
| 1 | Title | 0:20 |
| 2 | A pipeline runs and stops | 0:50 |
| 3 | The whole loop, one picture | 0:50 |
| 4 | Getting data off the machine | 1:00 |
| 5 | Four signals | 0:55 |
| 6 | What the ranking looks like | 0:55 |
| 7 | The selection component is built | 0:50 |
| 8 | Dataset manifest and the four pins | 1:00 |
| 9 | Gate on slices, never on the aggregate | 0:50 |
| 10 | Release a bundle, then roll it out | 1:00 |
| 11 | Buy managed, build only selection | 0:45 |
| 12 | What breaks first is not the cloud | 0:40 |
| 13 | The three edges that close the loop | 0:55 |
| 14 | Five trade-offs, with the cost stated | 0:40 |
| 15 | Three claims this design makes | 0:30 |
| 16 | Thank you | 0:15 |
| | **Total** | **12:15** |

Slides 6, 9 and 13 are the three that must land: the worked ranking, the hidden regression, and the closed loop.
If the clock runs short, 7 and 11 are the ones to compress.

## If asked to go deeper

| Question | Where the answer is |
|---|---|
| Full ranking example, all 8 clips | Technical Design §4 |
| All 47 trade-offs | Design Document §8 |
| The 12 stated assumptions | Design Document, *Assumptions* |
| Why each AWS service, and what was rejected | Design Document §5.1 |
| The code, its tests and example output | `../3-implementation/` |
