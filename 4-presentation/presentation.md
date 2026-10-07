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
    font-size: 22px;
    line-height: 1.45;
    padding: 48px 64px 54px 64px;
    letter-spacing: -0.005em;
  }

  h1 {
    font-size: 40px;
    font-weight: 700;
    color: #13293d;
    margin: 0 0 8px 0;
    letter-spacing: -0.02em;
  }
  h1::after {
    content: '';
    display: block;
    width: 68px;
    height: 4px;
    background: #d08a2e;
    margin-top: 15px;
  }
  h2 {
    font-size: 25px;
    font-weight: 600;
    color: #5b86b8;
    margin: 20px 0 8px 0;
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

  ul { margin: 10px 0; padding-left: 22px; }
  li { margin-bottom: 7px; }
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
  .note  { font-size: 18px; color: #46617d; margin-top: 15px; }

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
    padding: 13px 13px;
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
    padding: 11px 16px;
    margin: 9px 0;
    font-size: 19px;
  }
  .feedback .n { font-weight: 700; color: #d08a2e; margin-right: 10px; }

  .cost {
    color: #8a5a12;
    background: #fdf7ee;
    border-radius: 3px;
    padding: 1px 7px;
    font-weight: 600;
  }

  table { width: 100%; border-collapse: collapse; font-size: 17px; margin-top: 12px; }
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
  td { padding: 6px 9px; border-bottom: 1px solid #e3e8ee; vertical-align: top; }
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
Thank you for the time. I will walk through how field data gets off the machine, how we pick what is worth labelling, how models are trained and released, and how the loop closes on itself. The design starts from one fact: we can label about one percent of what we record.
-->

---

# A pipeline runs and stops. A flywheel keeps momentum

<div class="row">
<div class="box"><span class="t">Pipeline</span>New data arrives. The same steps run again. Each run costs what the last one cost and buys what the last one bought.</div>
<div class="box accent"><span class="t">Flywheel</span>Each turn makes the next turn cheaper, because information also flows backwards.</div>
</div>

<div class="lede">The feedback edges are the design. Take them out and this is a pipeline that is run often.</div>

<div class="note">Three edges, named and built: field failures fire retraining · weak evaluation slices steer the next collection · shadow disagreements become labelling candidates.</div>

<!--
This is the thesis. The forward path — ingest, select, label, train, evaluate, deploy — is necessary, but it is not a flywheel. What makes it one is three edges that carry information backwards. I come back to them at the end and show why the returns build rather than repeat.
-->

---

# The whole loop, one picture

<div class="row">
<div class="box"><span class="t">Vehicle</span>Sensors, recording, local buffer</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Ingest</span>Check, promote, catalogue</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Select</span>Keep about 1%</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Label</span>Pre-labelled export</div>
</div>

<div class="row">
<div class="box"><span class="t">Dataset</span>Fixed manifest</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Train</span>Four pins</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Evaluate</span>Slices and regression</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Release</span>Signed bundle, staged</div>
</div>

<!--
Here is the forward path. Data leaves the machine, is checked and catalogued, selection cuts the hours down, labels come back, a dataset version is built, a model is trained and tested, and a signed bundle goes out. Each stage owes the next one a guarantee. Nothing unchecked reaches a machine.
-->

---

# Getting data off the machine

<div class="row">
<div class="box"><span class="t">1 · Telemetry</span>Always on. Tiny.</div>
<div class="box"><span class="t">2 · Cellular clips</span>Flagged events only.</div>
<div class="box accent"><span class="t">3 · Depot WiFi</span>Bulk — about <strong>98% of bytes</strong>, near-zero cost.</div>
<div class="box"><span class="t">4 · Physical media</span>Sites with no link.</div>
</div>

<div class="row">
<div class="box gate"><span class="t">Integrity — hard fail</span>Did all the bytes arrive? Hashes, chunk counts, sequence gaps. → <strong>quarantine</strong></div>
<div class="box"><span class="t">Quality — soft flag</span>Is the data usable? Flagged, not dropped. A dusty lens is what selection wants. → <strong>raw</strong></div>
</div>

<div class="note"><span class="cost">Cost</span> Tier 3 assumes machines come back to a depot most days — the biggest assumption here, and tier 4 is its fallback. <strong>Calibration version is required at ingest:</strong> a mount that shifts raises no error, it just poisons every cross-sensor projection.</div>

<!--
Four transfer tiers, split by urgency and size. Depot WiFi carries most of the bytes cheaply. A durable buffer on the machine means an outage delays ingestion rather than losing data. At ingest, integrity hard-fails to quarantine but quality only flags, because a dusty lens is the material we want.
-->

---

# Four signals, because uncertainty cannot see confident error

<div class="row">
<div class="box accent"><span class="t">WRONG</span>Disengagement, emergency brake, near-miss. <strong>Needs no model.</strong></div>
<div class="box"><span class="t">UNSURE</span>Low confidence, narrow margin, unstable detection.</div>
<div class="box"><span class="t">CONFLICT</span>Camera and LiDAR disagree. Gated on clock sync.</div>
<div class="box"><span class="t">RARE</span>Gap against the scenario list.</div>
</div>

<div class="lede">A model that is certain and wrong is the worst case: the machine drives into it at full speed. Only WRONG and CONFLICT can see that clip.</div>

<div class="row">
<div class="box"><span class="t">Weights</span>WRONG counts most · then UNSURE · then CONFLICT · then RARE</div>
</div>

<div class="note"><span class="cost">Cost</span> More scoring machinery to build and keep running than plain uncertainty sampling.</div>

<!--
Classic active learning samples on uncertainty. Uncertainty is blind to the dangerous case: the model that is sure and wrong. Only the machine's own logged failures and cross-sensor conflict surface that clip. WRONG carries the most weight, needs no model, and so solves the cold start. Conflict is gated on clock sync, or working sensors look broken.
-->

---

# What the ranking looks like

| Clip | Outcome |
|---|---|
| Disengagement in dust | **Must-take** |
| LiDAR sees it, camera does not | **Selected** |
| Same dust, a minute later | **Deferred** — a near neighbour was already taken |
| Straight line, clear day | **Random** reserve |

<div class="two-col">
<div>
<h3>Quality multiplies</h3>
A faulty sensor looks maximally interesting. A subtracted penalty gets outvoted. A multiplier holds the clip back and raises a maintenance alert.
</div>
<div>
<h3>Three groups, not a top slice</h3>
Ranking the shortlist on the cheap signals admits only event clips, and excludes exactly what UNSURE and CONFLICT exist to find.
</div>
</div>

<div class="note">Every pick carries its reasons, so anyone can ask why we paid for a clip. The random reserve keeps evaluation honest — without it, normal-condition performance stops being measurable.</div>

<!--
Row two is the confident error: uncertainty is near zero, so uncertainty sampling drops it, and conflict rescues it. Row three has the same signals as row one but a near neighbour was already taken, so it is deferred, not discarded, and returns next cycle. Row four is below threshold and taken anyway, from the random reserve.
-->

---

# The selection component is built

<div class="row">
<div class="box"><span class="t">In</span>Clips with signals</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Filtered</span>Already labelled, too damaged</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Scored</span>Four signals, quality, diversity</div>
<div class="arrow">→</div>
<div class="box accent"><span class="t">Out</span>A shortlist, each pick with its reasons</div>
</div>

- **Each test name is a promise.** One proves the four-signal argument: uncertainty alone ranks the dangerous clip *last*.
- **Nothing is dropped silently.** Every skipped clip records a reason, and a test asserts that input equals dropped plus scored.
- **A missing signal is not a zero signal.** With no model yet, UNSURE returns nothing and the rest are reweighted.

<div class="note">Two dependencies. <code>docker compose up --build</code>. The run is repeatable: ties break on clip ID, and the manifest hashes the input.</div>

<!--
I built selection because it is the part whose returns build up, and because its scoring is deterministic and so genuinely testable. The test I would point at is the one asserting that uncertainty alone inverts the ranking. It turns a design argument into something that fails loudly if the code stops being true to it.
-->

---

# A dataset version is a manifest, and a run has four pins

<div class="row">
<div class="box"><span class="t">Fixed manifest</span>References plus content hashes, written once. A folder is editable — clips come and go and the name stays the same.</div>
<div class="box"><span class="t">Sticky splits</span>Set per session and never redrawn. Nearby frames are near-duplicates, so a frame split puts twins in train and test.</div>
<div class="box gate"><span class="t">Leakage check</span>Compares content, not IDs. A session ingested twice is one drive with two names.</div>
</div>

<div class="row">
<div class="box"><span class="t">Dataset hash</span></div>
<div class="box"><span class="t">Git SHA</span></div>
<div class="box accent"><span class="t">Image digest</span>not a tag</div>
<div class="box"><span class="t">Config and seeds</span></div>
</div>

<div class="note">A leaky split does not look like an error. It looks like success. <span class="cost">Cost</span> Sticky splits waste some data, but redrawing them breaks every past comparison. Reproducibility is statistical, not bitwise, and we say so — claiming more than we paid for is worse than claiming none.</div>

<!--
A dataset version is a fixed manifest with a hash per sample, checked at load. Splits are per session and never redrawn, because redrawing turns last version's test data into this version's training data. Four pins make a run repeatable, and the image pin is the one teams weaken: a tag is a moving pointer.
-->

---

# Gate on slices, never on the aggregate

<div class="row">
<div class="box"><span class="t">Aggregate</span><span style="font-size:40px;font-weight:700;color:#3f9c62;">+1.2</span><br>points overall. Looks like a clear win.</div>
<div class="box gate"><span class="t">Dust slice</span><span style="font-size:40px;font-weight:700;color:#b03a2e;">−5.7</span><br>points. For a machine in a dry field, that model is worse.</div>
</div>

<div class="lede">A small slice moves the headline number by almost nothing, so a bad regression inside it stays invisible — and the rare slices are the costly ones.</div>

- **A frozen evaluation set**, refreshed on purpose. A growing exam means models sat different tests.
- **A regression suite of real field incidents that only grows.** Nothing is removed, because the conditions have not stopped existing.

<!--
This is a real result from the design. Plus one point two overall, minus five point seven in dust. On the aggregate that model ships. For a machine in a dry field it is worse. So the gate is per slice, next to a frozen evaluation set and a regression suite of real incidents that only ever grows.
-->

---

# Release a bundle, then roll it out in stages

<div class="row">
<div class="box"><span class="t">Software</span></div>
<div class="box"><span class="t">Compiled models</span></div>
<div class="box"><span class="t">Config</span></div>
<div class="box"><span class="t">Calibration schema</span></div>
<div class="box"><span class="t">Hardware target</span></div>
</div>

<div class="row">
<div class="box gate"><span class="t">Gate</span>Seven conditions, six automatic, one named human approval</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Shadow</span>Live sensors, nothing actuated</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Canary</span>Live, supervised, known sites</div>
<div class="arrow">→</div>
<div class="box"><span class="t">Waves</span>Part of the fleet, soak, then the rest</div>
</div>

<div class="note">Accuracy depends on code around the model, so the bundle is the release unit. <strong>The artifact that trains is not the artifact that runs</strong> — quantising hurts low-contrast scenes most, so the compiled model is retested on target hardware. On the machine, two slots and an automatic revert, which works with no network and no human. <span class="cost">Cost</span> One bundle couples cadence: a one-line fix needs a full release.</div>

<!--
Shipping a model apart from the code around it is a trap: change a normalisation constant and behaviour changes without the model changing. So one signed bundle. Then shadow, canary, waves, with time and metric thresholds at each step. The gate is enforced twice, in the pipeline and again on the machine, which refuses unsigned bundles.
-->

---

# Buy managed, build only the selection logic

<div class="row">
<div class="box"><span class="t">Vehicle</span>Greengrass</div>
<div class="box"><span class="t">Ingest</span>IoT Core · Kafka · Firehose · S3</div>
<div class="box"><span class="t">Store</span>S3 Object Lock · Iceberg · Postgres</div>
<div class="box"><span class="t">Process</span>Batch on Spot · Glue · Athena</div>
<div class="box"><span class="t">Train</span>SageMaker · MLflow</div>
<div class="box"><span class="t">Deliver</span>Actions · ECR · Signer · IoT Jobs</div>
</div>

<div class="lede">The scarcest resource is not compute or storage. It is engineering attention.</div>

- **Buy managed unless managed forces a design compromise.** Kafka is the one bought exception — mine sites have no dependable link, so the streaming layer must be able to run locally.
- **Build only selection and curation.** The rest is plumbing, and plumbing is rented.

<!--
At this fleet size AWS absorbs the load almost however the architecture is drawn. What it cannot absorb is a few engineers running Kubernetes, Kafka and Spark while also building the thing that differentiates the company. Kafka is the one deliberate exception, bought for portability to sites with no cloud link.
-->

---

# What breaks first is not the cloud

| Binds first | Why | Response |
|---|---|---|
| **Depot upload bandwidth** | A link that serves five machines does not serve fifty | Cut more on the machine; grow the physical tier |
| **The labelling budget** | Ten times the data is not ten times the budget | Selection carries more weight |
| **Bench hardware for hardware-in-the-loop** | Scales with vehicle *variants*, not fleet size | One bench per variant; compile and test in parallel |

<!--
Scalability questions usually get answered with the cloud, and the cloud is the part that does not bind. What binds is physical and financial: depot bandwidth, the labelling budget, and bench hardware, which scales with vehicle variants rather than fleet size. I would rather name the revision points than claim the design is final.
-->

---

# The three edges that close the loop

<div class="feedback"><span class="n">①</span> <strong>Field failures → retraining.</strong> A deployed model's slice failure rate crosses a threshold and fires the pipeline that replaces it.</div>

<div class="feedback"><span class="n">②</span> <strong>Weak slices → next collection.</strong> A slice that scores badly gets more weight next cycle. Evaluation stops being a report and becomes an input.</div>

<div class="feedback"><span class="n">③</span> <strong>Shadow disagreements → selection pool.</strong> A frame two models disagree on is hard by construction. <em>Testing a model makes the data that improves the next one.</em></div>

<div class="note">Returns build rather than repeat: a random hour is worth less each cycle, so selection must get sharper · a better model pre-labels better, so the same budget buys more labelled hours · every release leaves new regression tests behind.</div>

<!--
Here is the loop closed. Field failures fire retraining. Weak slices get more weight in the next selection cycle. Shadow disagreements become labelling candidates, so testing a model makes the data that improves the next one. The returns build because a random hour is worth less every cycle, pre-labelling gets cheaper, and the test suite grows on its own.
-->

---

# Five trade-offs, with the cost stated

| Chose | Over | Cost accepted |
|---|---|---|
| Depot WiFi for most bytes | One upload path | Depends on a daily depot return; physical media is the fallback |
| Four selection signals | Uncertainty sampling alone | More scoring machinery to build and run |
| Sticky session splits | Random frame split | Wastes some data; splits cannot be balanced exactly |
| The bundle as release unit | Separate model and software deploys | A one-line fix needs a full release |
| Statistical reproducibility, stated | Bitwise determinism | Re-runs vary within normal variance |

<div class="note">The full register states each decision as <em>what was chosen · what it was chosen over · what it costs</em> — the named trade-offs matter more than the stack.</div>

<!--
Every decision in the document is written as what was chosen, what it was chosen over, and what it costs. These five carry the most weight. The first is the one I would most want challenged: the transfer design rests on machines returning to a depot most days, and if that fails, tier four is the fallback.
-->

---

<!-- _class: lead -->

# Three claims this design makes

<div class="lede"><strong>It is a flywheel, not a pipeline.</strong> Three feedback edges are named and built. Take them out and this is a pipeline that is run often.</div>

<div class="lede"><strong>Every gate fails closed.</strong> No stage produces output by default. A label batch, a dataset version, a model, a release bundle — each exists because a check passed, and failed attempts are recorded as fully as successful ones.</div>

<div class="lede"><strong>It is sized for this company, and it says where it stops.</strong> Every place that assumption binds is named, with the trigger that changes the decision.</div>

<!--
Three claims to close on. First, this is a flywheel rather than a pipeline, and the three edges are what make that true. Second, every gate fails closed, and the failed run is recorded as fully as the successful one. Third, it is sized for this company and it says where it stops. Thank you.
-->

---

<!-- _class: lead -->

# Thank you

<div class="lede">Happy to go deeper on any part of it — selection, the release gate, or how the loop closes.</div>

<div class="small">Nakshatra Vyas · Data Engineer — Autonomous Systems</div>

<!--
That is the design. Happy to go deeper on any part of it — the selection scoring, the release gate, or how the loop closes on itself.
-->
