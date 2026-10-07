---
marp: true
paginate: true
theme: default
style: |
  @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500&display=swap');

  section {
    background: #fbfbfd;
    color: #13293d;
    font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif;
    font-size: 24px;
    line-height: 1.5;
    padding: 56px 68px 72px 68px;
    letter-spacing: -0.005em;
  }

  h1 {
    font-size: 44px;
    font-weight: 700;
    color: #13293d;
    margin: 0 0 10px 0;
    letter-spacing: -0.02em;
  }
  h1::after {
    content: '';
    display: block;
    width: 68px;
    height: 4px;
    background: #d08a2e;
    margin-top: 20px;
  }
  h2 {
    font-size: 27px;
    font-weight: 600;
    color: #5b86b8;
    margin: 26px 0 10px 0;
    letter-spacing: -0.01em;
  }
  h3 {
    font-size: 21px;
    font-weight: 600;
    color: #13293d;
    margin: 18px 0 6px 0;
  }

  strong { color: #13293d; font-weight: 600; }
  em { color: #5b86b8; font-style: normal; font-weight: 500; }
  code {
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.88em;
    background: #eef2f7;
    color: #13293d;
    padding: 1px 6px;
    border-radius: 3px;
  }

  ul { margin: 14px 0; padding-left: 22px; }
  li { margin-bottom: 11px; }
  li::marker { color: #d08a2e; }

  .lede {
    font-size: 27px;
    line-height: 1.45;
    color: #13293d;
    border-left: 4px solid #d08a2e;
    padding-left: 22px;
    margin: 26px 0;
  }
  .small { font-size: 19px; color: #46617d; }
  .note  { font-size: 19px; color: #46617d; margin-top: 22px; }

  .row {
    display: flex;
    gap: 12px;
    align-items: stretch;
    margin: 24px 0;
  }
  .box {
    flex: 1;
    background: #ffffff;
    border: 1px solid #d3dde8;
    border-top: 3px solid #5b86b8;
    border-radius: 4px;
    padding: 16px 14px;
    font-size: 18px;
    line-height: 1.35;
  }
  .box .t {
    display: block;
    font-weight: 700;
    font-size: 16px;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: #13293d;
    margin-bottom: 8px;
  }
  .box.accent { border-top-color: #d08a2e; background: #fdf7ee; }
  .box.gate   { border-top-color: #b03a2e; background: #fcf0ee; }

  .arrow {
    align-self: center;
    color: #5b86b8;
    font-size: 26px;
    font-weight: 600;
    flex: 0 0 auto;
    padding: 0 2px;
  }

  .two-col { display: flex; gap: 42px; margin-top: 20px; }
  .two-col > div { flex: 1; }

  .big {
    font-size: 70px;
    font-weight: 700;
    color: #13293d;
    line-height: 1.05;
    letter-spacing: -0.03em;
  }
  .big .unit { font-size: 26px; font-weight: 600; color: #5b86b8; display: block; margin-top: 10px; letter-spacing: 0; }

  .feedback {
    background: #fdf7ee;
    border: 1px solid #e3c591;
    border-left: 4px solid #d08a2e;
    border-radius: 4px;
    padding: 14px 18px;
    margin: 12px 0;
    font-size: 20px;
  }
  .feedback .n { font-weight: 700; color: #d08a2e; margin-right: 10px; }

  .cost {
    color: #8a5a12;
    background: #fdf7ee;
    border-radius: 3px;
    padding: 1px 7px;
    font-weight: 600;
  }

  table { width: 100%; border-collapse: collapse; font-size: 18px; margin-top: 16px; }
  th {
    text-align: left;
    font-weight: 600;
    color: #5b86b8;
    border-bottom: 2px solid #5b86b8;
    padding: 7px 9px;
    font-size: 16px;
    letter-spacing: 0.04em;
    text-transform: uppercase;
  }
  td { padding: 7px 9px; border-bottom: 1px solid #e3e8ee; vertical-align: top; }
  tr:last-child td { border-bottom: none; }

  section::after {
    color: #9aa9b8;
    font-size: 15px;
    font-weight: 500;
  }

  section.lead {
    background: #13293d;
    color: #fbfbfd;
    justify-content: center;
  }
  section.lead h1 { color: #fbfbfd; font-size: 50px; }
  section.lead h2 { color: #d08a2e; margin-top: 0; }
  section.lead strong { color: #fbfbfd; }
  section.lead .lede { color: #e6ecf2; border-left-color: #d08a2e; }
  section.lead .small { color: #9fb3c8; }
  section.lead::after { color: #5b86b8; }
---

<!-- _class: lead -->

# Data Flywheel for Autonomous Systems

## Design for off-road perception at fleet scale

**Nakshatra Vyas** — Data Engineer, Autonomous Systems
Zensomy Autonomous Technologies · October 2026

<div class="small">Ingestion · selection · training · release · the three edges that close the loop</div>

<!--
Thank you for the time. Over the next twelve minutes I will walk through a complete design for the data flywheel: how field data gets off the machine, how we decide what is worth labelling, how models are trained and released, and how the loop closes. I want to start with the two numbers that force almost every decision in this design, because once you have seen them the rest follows.
-->

---

# Two numbers decide the architecture

<div class="two-col">
<div>
<div class="big">178 h<span class="unit">of upload for 8 hours of driving</span></div>
<div class="small">400 GB per vehicle-day against a 5 Mbps rural uplink. At $1–10/GB that is $400–4,000 per vehicle per day.</div>
</div>
<div>
<div class="big">~1%<span class="unit">of recorded footage can be annotated</span></div>
<div class="small">10,000 hours recorded against roughly 100 hours of annotation budget. The limit is financial, so more compute does not relieve it.</div>
</div>
</div>

<div class="lede">Streaming everything to the cloud is not a rejected trade-off. It is impossible. And labelling everything that does arrive is impossible too.</div>

<!--
Four hundred gigabytes per machine per day over a five megabit rural link is a hundred and seventy-eight hours of upload for eight hours of driving, and the cellular bill runs to several thousand dollars per machine per day. So the vehicle has to decide what leaves. The second number is annotation: we can label about one percent of what we record, and that limit is financial rather than technical, so no amount of compute relieves it. Every decision downstream is an answer to one of these two numbers.
-->

---

# A pipeline runs and stops. A flywheel stores momentum

<div class="row">
<div class="box"><span class="t">Pipeline</span>New data arrives. The same steps run again. Each run costs what the last one cost and buys what the last one bought.</div>
<div class="box accent"><span class="t">Flywheel</span>Each turn makes the next turn cheaper and more productive, because information flows backwards as well as forwards.</div>
</div>

<div class="lede">The feedback edges are the design. Remove them and this is a pipeline that happens to be run repeatedly.</div>

<div class="note">Three edges, named and mechanised: field failures fire retraining · weak evaluation slices steer the next collection · shadow-mode disagreements become annotation candidates.</div>

<!--
This is the thesis of the whole submission. The forward path — ingest, select, annotate, train, evaluate, deploy — is necessary but it is not a flywheel. What makes it a flywheel is three edges that carry information backwards: field failures that fire retraining, weak evaluation slices that steer the next collection, and shadow-mode disagreements that become annotation candidates. I will come back to those at the end and show why the returns compound rather than repeat.
-->

---

# The whole loop, one picture

<div class="row">
<div class="box"><span class="t">Vehicle</span>Sensors, recording, local buffer</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Ingest</span>Verify, promote, catalogue</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Select</span>10,000 h → 100 h</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Annotate</span>Pre-labelled export</div>
</div>

<div class="row">
<div class="box"><span class="t">Dataset</span>Immutable manifest</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Train</span>Four pins</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Evaluate</span>Slices + regression</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Release</span>Signed bundle, staged</div>
</div>

<div class="feedback"><span class="n">↑</span> Three dotted edges run backwards from release and evaluation into training and selection — <strong>solid lines are data, dotted lines are decisions.</strong></div>

<!--
Here is the forward path end to end. Data leaves the vehicle, is verified and catalogued, selection cuts ten thousand hours to a hundred, annotation returns labels, a dataset version is built, a model is trained and evaluated, and a signed bundle is staged out to the fleet. Every stage owes the next one a guarantee. Nothing in the raw zone is incomplete or mutable. No model candidate exists without evidence attached. Nothing unvalidated reaches a machine.
-->

---

# The vehicle decides what leaves, in four tiers

<div class="row">
<div class="box"><span class="t">1 · Cellular telemetry</span>Always on. Kilobytes per second.</div>
<div class="box"><span class="t">2 · Cellular clips</span>Flagged events only.</div>
<div class="box accent"><span class="t">3 · Depot WiFi</span>Bulk — about <strong>98% of bytes</strong>, at near-zero marginal cost.</div>
<div class="box"><span class="t">4 · Physical media</span>Sites with no usable link.</div>
</div>

- **Durable local buffer, store-and-forward** — a cloud or link outage delays ingestion, it does not lose data. The most important reliability property in the system lives on the vehicle, not in the cloud.
- **Priority queue, not FIFO** — when the buffer fills or a link returns briefly, flagged data goes first.
- **Idempotent keys and resumable multipart upload** — over unreliable links, unknown completion state is the normal case.

<div class="note"><span class="cost">Cost</span> Tier 3 depends on machines returning to a depot most days. That is the most load-bearing assumption in the design, and tier 4 is its explicit fallback.</div>

<!--
Four transfer tiers split by urgency and size. Cellular carries only what must be timely. Depot WiFi carries about ninety-eight percent of the bytes at near-zero marginal cost. Physical media covers sites with no usable link. Underneath all of it is a durable local buffer, so an outage delays ingestion rather than losing data — and notice that property lives on the machine, not in the cloud. The honest cost is that tier three assumes a daily depot return, and I have named tier four as the fallback if that assumption fails.
-->

---

# Integrity and quality are two different problems

<div class="row">
<div class="box gate"><span class="t">Integrity — hard fail</span>Did all the bytes arrive intact? Manifest reconciliation, SHA-256 per chunk, chunk count, sequence continuity.<br><br>→ <strong>quarantine/</strong>, 90 days for diagnosis</div>
<div class="box"><span class="t">Quality — soft flag</span>Is the data usable? Structural, temporal, signal-level, semantic.<br><br>→ <strong>raw/</strong>, ingested and flagged, visible to selection</div>
</div>

<div class="lede">A truncated upload must never become canonical data. A dusty lens must never be thrown away — it is exactly the material selection wants.</div>

## The silent poisoner

**Calibration version is a mandatory field at ingest.** A mount that shifts two centimetres without re-calibration invalidates every LiDAR-to-camera projection from that moment on. Nothing fails. No error is raised. Models trained on the mixture degrade and the cause is untraceable unless the version was recorded.

<!--
Conflating integrity and quality is the common error. Integrity asks whether the bytes arrived; it hard-fails to quarantine, and a rising quarantine rate on one machine is a hardware signal rather than noise. Quality asks whether the data is usable; it only soft-flags, because a dusty lens is the material we actually want. Separately, calibration version is mandatory at ingest. A mount that shifts two centimetres raises no error at all — it just silently poisons every cross-sensor projection, and without the recorded version the cause is untraceable.
-->

---

# Four signals, because uncertainty cannot see confident error

<div class="row">
<div class="box accent"><span class="t">WRONG · 0.35</span>Disengagement, emergency brake, near-miss, re-plan storm. <strong>Needs no model.</strong></div>
<div class="box"><span class="t">UNSURE · 0.30</span>Low confidence, narrow margin, detection instability.</div>
<div class="box"><span class="t">CONFLICT · 0.20</span>Camera and LiDAR disagree. Gated on clock sync under 10 ms.</div>
<div class="box"><span class="t">RARE · 0.15</span>Coverage gap against the scenario taxonomy.</div>
</div>

<div class="lede">The model that is 97% certain and wrong is the highest-risk failure mode, because the machine proceeds at full speed into it. Only WRONG and CONFLICT can see it.</div>

- **WRONG also solves the cold start** — a disengagement is a trained operator judging the machine unsafe, and it needs no model at all.
- **CONFLICT is gated** — at 200 ms of skew, correctly functioning sensors appear to disagree on every frame.

<div class="note"><span class="cost">Cost</span> Four signals over classic uncertainty sampling: more scoring machinery to build and maintain.</div>

<!--
Classic active learning samples on uncertainty. The problem is that uncertainty is blind to the single most dangerous case: the model that is ninety-seven percent certain and wrong, because the machine then proceeds at full speed into a situation it has misread. Only the vehicle's own logged failures and cross-sensor conflict can surface that clip. WRONG carries the heaviest weight, needs no model, and therefore solves the cold start. Conflict is gated on clock synchronisation, because two hundred milliseconds of drift makes working sensors look broken.
-->

---

# Scoring, diversity, and the budget

<div class="small"><code>score = (0.35·WRONG + 0.30·UNSURE + 0.20·CONFLICT + 0.15·RARE) × quality ÷ similarity</code></div>

| Clip | WRONG | UNSURE | CONFLICT | RARE | Qual | Sim | Score | Outcome |
|---|---|---|---|---|---|---|---|---|
| `veh03` disengagement, dust | 1.00 | 0.71 | 0.44 | 0.92 | 0.95 | 1.0 | **0.750** | Must-take |
| `veh04` LiDAR sees it, camera does not | 0.80 | **0.12** | 0.78 | 0.55 | 0.93 | 1.0 | **0.516** | Selected |
| `veh03` same dust, 90 s later | 1.00 | 0.68 | 0.41 | 0.92 | 0.95 | **2.4** | **0.310** | Deferred |
| `veh01` straight line, clear day | 0.00 | 0.08 | 0.05 | 0.05 | 1.00 | 1.0 | **0.042** | Random 10% |

<div class="small"><strong>Budget:</strong> 20% must-take · 70% scored and diversity-attenuated · 10% random · 15% per-vehicle cap</div>

<!--
This is the concrete output: a ranked list with every term visible, so any selection can be explained. Row two is the confident error — uncertainty is zero point one two, so uncertainty sampling would discard it, and conflict is what rescues it. Row three has identical raw signals to row one but a similarity divisor of two point four, because near-neighbours were already taken; it is deferred, not discarded, and returns next cycle. Row four is below threshold and selected anyway, from the ten percent random reservation.
-->

---

# Two structural choices in that score

<div class="two-col">
<div>
<h3>Quality multiplies, it does not subtract</h3>
A faulty sensor produces high uncertainty <em>and</em> high cross-sensor conflict at once. An additive penalty gets outvoted by four strong signals. A multiplier suppresses the clip regardless of how strongly it scores elsewhere — and raises a maintenance alert instead.
</div>
<div>
<h3>The shortlist is three groups, not a top-N</h3>
At shortlist time only WRONG and RARE have been computed. Ranking on those admits almost exclusively event-bearing clips and <strong>systematically excludes what UNSURE and CONFLICT exist to find.</strong> The funnel becomes self-confirming.
</div>
</div>

<div class="feedback"><span class="n">10%</span> The random reservation preserves evaluation validity. If every labelled clip was chosen because the model struggled, normal-condition performance becomes unmeasurable — and it is the only mechanism that can surface a failure mode no signal was designed to detect.</div>

<div class="note"><span class="cost">Cost</span> A larger shortlist means higher GPU cost at the scoring stage · 10% of the budget is not optimised for information value.</div>

<!--
Two choices here are easy to get wrong. First, quality multiplies rather than subtracts, because a broken sensor looks maximally interesting — high uncertainty and high disagreement together — and a subtracted penalty simply gets outvoted. Second, the shortlist takes all events, all rare scenarios, and a random sample of the ordinary, rather than the top ten percent by cheap score. Pre-selecting on the signals you already have makes the expensive stage confirm what you know rather than discover what you do not.
-->

---

# The selection component is implemented

<div class="row">
<div class="box"><span class="t">In</span>6,000 clips</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Filtered</span>62 already labelled<br>205 too damaged</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Scored</span>5,733 clips</div>
<div class="arrow">→</div>
<div class="box accent"><span class="t">Out</span>55 clips, each with its reasons</div>
</div>

- **73 tests, and each name is a promise the design makes.** `test_uncertainty_alone_would_invert_the_ranking` proves the four-signal argument by showing that uncertainty alone ranks the dangerous clip *last*.
- **Nothing is dropped silently.** Every skipped clip carries a recorded reason, every limit that bound is named in the report, and a test asserts `input = dropped + scored`.
- **A missing signal is not a zero signal.** With no model yet, UNSURE returns nothing and the remaining signals are reweighted — scoring it zero would punish a clip for which subsystems happened to be reporting.

<div class="note">Two dependencies — numpy and pydantic. <code>docker compose up --build</code>, and the run is deterministic: ties break on clip ID, and the manifest hashes the input.</div>

<!--
I implemented the selection stage because it is the component whose returns compound, and because its scoring is deterministic and therefore genuinely testable. Six thousand clips in, fifty-five out, every pick carrying its reasons so anyone can ask why we paid for a clip. The test I would point at is the one asserting that uncertainty alone inverts the ranking — it turns a design argument into something that fails loudly if the code stops being true to it.
-->

---

# A dataset version is a manifest, not a folder

<div class="row">
<div class="box"><span class="t">Immutable manifest</span>References plus content hashes, written once. A folder is mutable — someone removes a clip, corrects fifty labels, appends a batch, and the name stays <code>v4</code>.</div>
<div class="box"><span class="t">Sticky session splits</span>Assigned by <code>hash(session_id)</code>, never re-drawn. Consecutive frames are near-duplicates, so a random frame split puts a frame in train and its twin in test.</div>
<div class="box gate"><span class="t">Independent leakage check</span>Compares <strong>content</strong> — exact hashes plus near-duplicate embeddings — not identifiers. A session re-ingested under a new ID is one drive with two names.</div>
</div>

<div class="lede">A leaky split does not present as an error. It presents as success: the score comes back high, stable, and unrelated to field performance.</div>

<div class="note"><span class="cost">Cost</span> Sticky splits are less data-efficient and cannot be balanced precisely — but re-drawing them invalidates every historical model comparison, and that loss is unrecoverable.</div>

<!--
A dataset version is an immutable manifest of references with a content hash per sample, verified at load, so a changed file aborts the run instead of silently training on different data. Splits are at session level and permanently sticky, because consecutive frames are near-duplicates and because re-drawing splits turns last version's test data into this version's training data. The leakage check is a separate step comparing content rather than identifiers, since a re-ingested session is one physical drive with two IDs.
-->

---

# Reproducibility: four pins, and an honest claim

<div class="row">
<div class="box"><span class="t">Dataset hash</span></div>
<div class="box"><span class="t">Git SHA</span></div>
<div class="box accent"><span class="t">Image digest</span>not a tag</div>
<div class="box"><span class="t">Config + seeds</span></div>
</div>

- **The environment pin is the one usually weakened.** An image tag is a mutable pointer — `:latest` resolves differently over time, and CUDA, driver and library versions shift with no record in the run.
- **Reproducibility is statistical, not bitwise, and we say so.** Bit-identical reproduction costs roughly 20–30% throughput for a property rarely needed.
- **Every run is recorded automatically** — inputs, metrics, artifacts, lineage. A run that is not recorded did not happen.

<div class="lede">Claiming stronger reproducibility than has been paid for is worse than claiming none, because someone will rely on it.</div>

<!--
Four pins: dataset hash, git SHA, container image digest, and config plus seeds. The environment pin is the one teams usually weaken, and an image tag is a mutable pointer — CUDA and driver versions shift underneath it with no record. On reproducibility I make a deliberately weaker claim than is fashionable: statistical, not bitwise. Bitwise costs twenty to thirty percent throughput for a property almost nobody needs, and overclaiming it is worse than not claiming it, because someone will rely on it.
-->

---

# Evaluation gates per slice, never on the aggregate

<div class="row">
<div class="box"><span class="t">Aggregate</span><span style="font-size:40px;font-weight:700;color:#3f9c62;">+1.2</span><br>points overall. Looks like a clear improvement.</div>
<div class="box gate"><span class="t">Dust slice</span><span style="font-size:40px;font-weight:700;color:#b03a2e;">−5.7</span><br>points. For a machine in a dry field, that model is worse.</div>
</div>

<div class="lede">A scenario that is 3% of the evaluation set contributes 3% of the aggregate, so a severe regression confined to it is invisible — and the rare slices are exactly the costly ones.</div>

- **A frozen evaluation set**, refreshed quarterly and deliberately. A growing exam means successive models sat different tests.
- **A regression suite of real past field incidents, which only grows.** Entries are never removed, because the conditions that produced them have not stopped existing.

<div class="note"><span class="cost">Cost</span> More evaluation compute, and occasional noisy failures on small slices — managed with minimum slice sizes and tolerance bands.</div>

<!--
This is a real result from the design. Plus one point two overall, minus five point seven in dust. On the aggregate that model ships. For a machine working a dry field it is strictly worse, and the aggregate hid it, because a slice that is three percent of the evaluation set moves the headline number by almost nothing. So the gate is per slice. Alongside it sits a frozen evaluation set and a regression suite of real field incidents that only ever grows.
-->

---

# The release unit is a bundle, never a model alone

<div class="row">
<div class="box"><span class="t">Software image</span></div>
<div class="box"><span class="t">Compiled models</span></div>
<div class="box"><span class="t">Config</span></div>
<div class="box"><span class="t">Calibration schema</span></div>
<div class="box"><span class="t">Hardware target</span></div>
</div>

**Why one unit.** A model's accuracy depends on pre- and post-processing that live in the software. Change the normalisation constants or the NMS threshold and the model behaves differently *without the model changing*. A model validated against software v12 has no established behaviour under v13.

## The compilation gap

**The artifact that trains is not the artifact that runs.** It is exported, quantised and compiled for the vehicle's accelerator, and quantisation degrades low-contrast inputs disproportionately — exactly the rare, costly slices. In this design **v7 passed dust at FP32 and failed it at INT8.** So the compiled engine is re-evaluated on target hardware.

<div class="note"><span class="cost">Cost</span> One bundle couples release cadence — a one-line fix requires a full release and full validation. A separate schema-validated configuration path exists so threshold changes do not create pressure to bypass the process.</div>

<!--
Deploying a model independently of the software that wraps it is a trap, because changing a normalisation constant changes the model's behaviour without changing the model. So the release unit is one signed bundle. The second point here is the compilation gap: the artifact that trains is not the artifact that runs. Version seven passed dust at full precision and failed it at INT8. Skip the re-evaluation and the model you validated and the model you shipped are different objects — and the deployed one carries a report saying it passed.
-->

---

# A seven-condition gate, then a staged rollout that reverts itself

<div class="row">
<div class="box"><span class="t">Gate — 7 conditions</span>Traceability · software tests · replay · compiled-model evaluation on target · hardware-in-the-loop · signature · <strong>one named human approval</strong></div>
<div class="arrow">→</div>
<div class="box"><span class="t">Shadow · 3 machines</span>Live sensors, outputs logged, never actuated. ≥20 operating hours, zero exposure.</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Canary · 2 machines</span>Live, supervised, known sites. ≥50 hours.</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Waves</span>25% of the fleet, ≥72-hour soak, then the remainder.</div>
</div>

- **The gate is enforced twice** — in the pipeline, and again on the vehicle. The two fail independently: a pipeline can be bypassed with sufficient access, but a vehicle that refuses unsigned bundles cannot be made to accept one remotely.
- **Dual-slot A/B with automatic revert on a failed boot health check** — rollback works with *no network and no human*, which is exactly the state a bad bundle creates.
- **Bundle version is recorded in every recording's session metadata.** Data cannot be rolled back; a defective model that ran six hours produced six hours of recordings.

<div class="note"><span class="cost">Cost</span> Named human approval and time-in-stage thresholds add roughly a week to reach the full fleet. Not the binding constraint on a weekly cadence.</div>

<!--
Validated is given an operational definition: seven conditions, six automatic, one a named human approval — because the blast radius here is physical machines near people, and the approver is recording accountability rather than re-deriving evidence. Rollout is shadow, then canary, then waves, with both time-in-stage and metric thresholds at every transition. On the machine, dual-slot A/B reverts automatically with no network and no human. And every recording carries the bundle version, because data cannot be rolled back.
-->

---

# Cloud: managed by default, and two rules behind it

<div class="row">
<div class="box"><span class="t">Vehicle</span>IoT Greengrass</div>
<div class="box"><span class="t">Ingest</span>IoT Core · MSK (Kafka) · Firehose · presigned S3 upload</div>
<div class="box"><span class="t">Store</span>S3 with Object Lock on raw · Iceberg + Glue Catalog · RDS PostgreSQL</div>
<div class="box"><span class="t">Process</span>Batch on Spot · Glue · Athena</div>
<div class="box"><span class="t">Train</span>SageMaker · MLflow</div>
<div class="box"><span class="t">Deliver</span>GitHub Actions · ECR · Signer · IoT Jobs</div>
</div>

<div class="lede">The scarcest resource is not compute or storage. It is engineering attention.</div>

- **Buy managed unless managed forces a design compromise.** Kafka is the exception bought deliberately — mining sites will have no dependable cloud link, and the streaming layer is the one component that must then run locally.
- **Build only the selection and curation logic.** Everything else is plumbing, and plumbing should be rented.
- **Two orchestrators, one rule.** Step Functions for thousands of short per-recording verifications; Airflow for the dependency-rich, backfillable pipeline DAGs.

<div class="note">Deliberately not used: EKS · Redshift · DynamoDB · Aurora · multi-region active-active. <span class="cost">Cost</span> Less control, and two orchestrators engineers must tell apart.</div>

<!--
At tens of machines AWS absorbs this load almost regardless of how the architecture is drawn. What it cannot absorb is a few engineers operating Kubernetes, Kafka and Spark clusters while also building the thing that differentiates the company. So: buy managed unless managed forces a compromise, and build only the selection and curation logic. Kafka is the one deliberate exception, bought for portability to mining sites with no cloud link. The list of what I deliberately did not use is as considered as the list of what I did.
-->

---

# What breaks first is not the cloud

| Binds first | Why | Response |
|---|---|---|
| **Depot upload bandwidth** | A link serving 5 machines does not serve 50 | More aggressive on-vehicle reduction; the physical tier expands |
| **The annotation budget** | Ten times the data is not ten times the budget | Selection carries more weight — its compounding argument |
| **Bench hardware for hardware-in-the-loop** | Scales with vehicle *variants*, not fleet size | Per-variant benches; parallel compile-and-evaluate stages |

<div class="small"><strong>Evolution path, in the order it should happen:</strong> per-variant bundles when verticals multiply → a learned ranker when hand-tuned weights stop being obviously right → expanded pre-labelling when annotation throughput binds → distributed training when datasets outgrow a single node → Kafka moved on-prem when customer sites appear.</div>

<div class="note">Sized for tens of machines now and low hundreds within three years — explicitly not 10,000. Every place that assumption binds is named, along with the trigger that changes the decision.</div>

<!--
Scalability questions usually get answered with the cloud, and here the cloud is the part that does not bind. What binds is physical and financial: depot upload bandwidth, the annotation budget, and bench hardware for hardware-in-the-loop, which scales with vehicle variants rather than fleet size. The design is sized for tens of machines now and low hundreds within three years, and I would rather name the revision points than claim the architecture is final.
-->

---

# The three edges that close the loop

<div class="feedback"><span class="n">①</span> <strong>Field failures → retraining.</strong> A deployed model's slice-level failure rate crosses a threshold and triggers the pipeline that replaces it. The deployed model's own failures fire its replacement.</div>

<div class="feedback"><span class="n">②</span> <strong>Weak evaluation slices → next collection.</strong> A slice that scores badly raises its weight in the next selection cycle. Evaluation stops being a report and becomes an input.</div>

<div class="feedback"><span class="n">③</span> <strong>Shadow disagreements → selection pool.</strong> A frame on which two independently trained models disagree is difficult by construction. <em>Validating a model produces the data that improves the next one.</em></div>

## Why the returns compound rather than repeat

- As the model improves, the share of footage it already handles grows — so **the value of a randomly chosen hour falls every cycle.** Selection must get smarter simply to hold its value constant.
- The production model pre-labels clips before annotation, so **a better model makes annotation cheaper** — the same budget buys more labelled hours each cycle.
- Every release contributes new regression tests and new replay sessions, so **the test suite strengthens as a by-product of shipping.**

<!--
Here is the loop closed. Field failures fire retraining. Weak evaluation slices raise their weight in the next selection cycle. Shadow disagreements become annotation candidates — so validating a model produces the data that improves the next one. And the returns compound rather than repeat for three reasons: a random hour is worth less every cycle, which forces selection to improve; a better model pre-labels, so the same annotation budget buys more; and every release leaves the test suite stronger.
-->

---

# Five trade-offs, with the cost stated

| Chose | Over | Cost accepted |
|---|---|---|
| Depot WiFi for ~98% of bytes | One upload path | **Depends on a daily depot return.** Physical media is the named fallback |
| Four selection signals | Uncertainty sampling alone | More scoring machinery to build and maintain |
| Session-level sticky splits | Random frame split | Less data-efficient; splits cannot be balanced precisely |
| The bundle as the release unit | Independent model and software deploys | Couples release cadence — a one-line fix needs full validation |
| Statistical reproducibility, stated | Bitwise determinism | Re-runs vary within normal run-to-run variance |

<div class="note">The full register is 47 entries, each stated as <em>what was chosen · what it was chosen over · what it costs</em> — because identified trade-offs matter more than the stack selected.</div>

<!--
Every decision in the document is written as what was chosen, what it was chosen over, and what it costs — forty-seven of them. These five carry the most weight. The first is the one I would most want challenged: the whole transfer architecture rests on machines returning to a depot most days, and if that assumption fails, tier four is what the design falls back to. I would rather name that dependency than hide it inside an architecture diagram.
-->

---

<!-- _class: lead -->

# Three claims this design makes

<div class="lede"><strong>It is a flywheel, not a pipeline.</strong> Three feedback edges are named and mechanised. Remove them and this is a pipeline that is run repeatedly.</div>

<div class="lede"><strong>Every gate fails closed.</strong> No stage produces output by default. A label batch, a dataset version, a model candidate, a release bundle — each exists only because a specific check passed, and the failed attempt is recorded as completely as the successful one.</div>

<div class="lede"><strong>It is sized for this company, and it says where it stops.</strong> Every place that assumption binds is named, along with the trigger that would change the decision.</div>

<div class="small">Thank you. Happy to go deeper on selection, the release gate, or the cost model.</div>

<!--
Three claims to close on. First, this is a flywheel rather than a pipeline, and the three edges are what make that true. Second, every gate fails closed — nothing in this system produces output by default, and the failed run is recorded as completely as the successful one. In the worked example the most useful run of the cycle was the one that failed. Third, it is sized for this company and it says where it stops. Thank you — I am happy to go deeper anywhere.
-->
