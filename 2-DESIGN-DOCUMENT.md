# Design Document — Data Flywheel for Autonomous Systems

**Nakshatra Vyas** · Data Engineer — Autonomous Systems · October 2026

**Deliverable 2** — the major design decisions and the assumptions behind them.
The architecture itself is in `1-TECHNICAL-DESIGN.md`; the code is in `3-implementation/`.

Every decision below is stated as **what was chosen · what it was chosen over · what it costs**, because the brief states that identified trade-offs matter more than the stack selected.

---

## Requirement coverage

Where each item the brief asks for is answered.

| Task | Brief asks for | Answered in |
|---|---|---|
| **1** | How data is transferred from the vehicle | Design §1.1 · Architecture §3 |
| | How recordings are organised and identified | Design §1.2 |
| | How metadata is associated with the data | Design §1.3 |
| | How data integrity and quality can be maintained | Design §1.4 |
| | How the solution handles unreliable connectivity | Design §1.5 |
| | How the system scales as vehicles increase | Design §1.6 · §7 |
| | *Deliverable: architecture + key design decisions* | Architecture §3 · Design §1 |
| **2** | Approach to identifying the most valuable data | Design §2 · Architecture §4 |
| | *Deliverable: an example of how data is ranked or prioritised* | **Architecture §4, worked ranking example** |
| **3** | Dataset creation and versioning | Design §3.1 |
| | Reproducible model training | Design §3.3 |
| | Model evaluation | Design §3.4 |
| | Experiment tracking | Design §3.5 |
| | Model / artifact management | Design §3.6 |
| | Re-running the pipeline when new data arrives | Design §3.7 |
| | *Deliverable: workflow from new dataset → training → evaluation → candidate* | Architecture §5 |
| **4** | Software changes | Design §4.1 |
| | ML / model changes | Design §4.2 |
| | Preventing unvalidated changes reaching a vehicle | Design §4.3 · §4.4 |
| | *Deliverable: workflow from change → validation → deployment* | Architecture §6 |
| **5** | Scalability | Design §5 |
| | Reliability | Design §5 |
| | Cost | Design §5 |
| | Data storage | Design §5 |
| | Compute | Design §5 |
| | Security | Design §5 |
| | Automation | Design §5 |
| | *Deliverable: high-level cloud architecture* | Architecture §7 |
| **6** | Source code · README · tests · example I/O · design notes | `3-implementation/` |

---

## Assumptions

Stated explicitly, as the brief invites. Each one is load-bearing somewhere.

| # | Assumption | Where it binds |
|---|---|---|
| 1 | Off-road machines in **GNSS-degraded, connectivity-poor** environments | All of §1 |
| 2 | Machines **return to a depot most operating days**, with high-bandwidth local network | **The most load-bearing assumption in the design.** §1.1 gives the fallback if it is false |
| 3 | Roughly **8 operating hours per vehicle-day** | Volume arithmetic |
| 4 | **~40–60 GB per vehicle-hour** → ~400 GB/vehicle-day. 4–6 cameras, 1 LiDAR, 1–2 radar, GNSS/INS, CAN | Transfer architecture |
| 5 | On-vehicle software is **ROS 2**; recordings written as **MCAP** | Format decisions |
| 6 | Sensor clocks synchronised by GNSS or PTP; **residual skew is measured, not assumed zero** | Cross-sensor signals in §2 |
| 7 | **Annotation is performed off-platform** — external vendor or internal tool, integrated over an API. Building an annotation tool is out of scope | §3 owns the handoff, not the tool |
| 8 | Cloud is **AWS**; §5 marks where the reasoning is portable | §5 |
| 9 | Scale target: **tens of vehicles now, low hundreds within 2–3 years.** Explicitly not 10,000 | Every sizing decision |
| 10 | **Annotation is the dominant marginal cost**, and the annotation ceiling is a small and shrinking fraction of what is recorded. The specific figure — 100 hours in the worked example — is an input, not a constant | Why §2 carries disproportionate weight; the ceiling is a config value, never hard-coded |
| 11 | Raw retention: 12 months instantly accessible, then deep archive, retained rather than deleted | Cost model |
| 12 | A trained perception model exists from cycle one; §2.7 covers operating before one does | Selection bootstrapping |

---

## 1 · Ingestion and management

**The constraint is arithmetic, not preference.** 400 GB per vehicle-day against a 5 Mbps rural uplink is **178 hours of upload for 8 hours of driving**, and at $1–10/GB the cellular bill is **$400–4,000 per vehicle per day**. Streaming everything to the cloud is not a trade-off that was considered and rejected; it is impossible. Every decision below follows from that.

### 1.1 How data is transferred

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Four transfer tiers** split by urgency and size — cellular telemetry, cellular flagged clips, depot WiFi bulk, physical media | One upload path | Cellular carries only what must be timely; depot WiFi carries ~98% of bytes at near-zero marginal cost | Depends on assumption 2. Tier 4 is the explicit fallback |
| **Resumable multipart upload**, chunk-level | Whole-file transfer | A dropped link mid-transfer resumes rather than restarts | More parts to track |
| **Priority queue on the vehicle**, not FIFO | First-in-first-out buffer | When the buffer fills or a link returns briefly, flagged data goes first and routine data waits | Requires a priority policy, which is a judgement call |

### 1.2 How recordings are organised and identified

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **MCAP, 60-second chunks** | Whole-session files; raw rosbag | MCAP is indexed — session metadata is readable from a few MB of a 10 GB file, which is what makes cataloguing affordable. Chunking makes upload resumable and bounds the loss from a corrupt write | More objects to track |
| **ULID session identifiers generated on-vehicle** | Server-assigned IDs; UUIDv4 | A machine in a field cannot reach a server to request an ID. ULIDs are collision-free offline and sort by time | Slightly larger keys than an integer |
| **Hive-style partitioning** — `vehicle_id=…/date=…/session=…` | Flat prefixes | Queries skip irrelevant partitions entirely; this is the main query-performance lever | Partition layout is hard to change later |
| **Idempotent keys throughout** | Retry bookkeeping and dedup logic | Over unreliable links, unknown completion state is the normal case. Deterministic keys make retry unconditionally safe and collapse a whole class of failure handling | Keys must be derivable without server state |

### 1.3 How metadata is associated

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Four metadata levels** — fleet, vehicle, session, chunk | Flat metadata per file | Fleet-wide facts are not duplicated across millions of chunks, and chunk-level facts are not lost inside session summaries | Schema complexity |
| **Manifest sidecar *and* a catalog** | Catalog only | The manifest makes a session self-describing even if the catalog is lost or has to be rebuilt — and it is what integrity verification reconciles against | Two artifacts to keep in step |
| **Calibration version as a first-class required field** | Assume calibration is stable | A mount that shifts two centimetres without re-calibration silently invalidates every LiDAR-to-camera projection from that moment on. **Nothing fails and no error is raised.** Models trained on the mixture degrade and the cause is untraceable unless the version was recorded at ingestion | One more mandatory field, enforced at ingest |
| **Clock-synchronisation quality recorded per session** | Assume clocks agree | 200 ms of skew at 10 km/h displaces observations by 0.56 m. Downstream consumers need to know how much to trust cross-sensor alignment | One more field |

### 1.4 How integrity and quality are maintained

**These are two different problems and conflating them is the common error.**

```mermaid
graph LR
    U["uploaded recording"] --> I{{"INTEGRITY<br/>Did all the bytes arrive intact?"}}
    I -->|"fail — hard"| Q["quarantine/<br/>90 days, diagnosis"]
    I -->|"pass"| QU{{"QUALITY<br/>Is the data usable?"}}
    QU -->|"fail — soft flag"| R["raw/ — ingested, flagged<br/>visible to selection"]
    QU -->|"pass"| R
    Q -.->|"rising rate on one vehicle"| M["maintenance signal"]

    classDef gate fill:#fdecea,stroke:#c0392b,stroke-width:2px,color:#7b241c
    classDef store fill:#eef4fb,stroke:#5b86b8,color:#13293d
    class I,QU gate
    class Q,R,M store
```

A dusty lens fails quality and is kept — it is exactly the material selection wants. A truncated upload fails integrity and must never become canonical data.

| | Integrity | Quality |
|---|---|---|
| Question | Did all the bytes arrive intact? | Is the data usable? |
| Checks | Manifest reconciliation, SHA-256 per chunk, chunk count, sequence continuity | Structural, temporal, signal-level, semantic |
| On failure | **Hard fail** → quarantine | **Soft flag** → ingested, annotated, visible downstream |

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Separate hard-fail and soft-flag paths** | One validation step | A corrupt transfer must never become canonical data. A dusty lens must not be thrown away — it is exactly the material §2 wants | Two code paths |
| **`landing/` → `raw/` promotion**, raw immutable with Object Lock | Write directly to the final location | A partial upload never becomes canonical. Corrections are new versions, never edits — which is what makes dataset manifests (§3.1) and replay testing (§4.1) safe | Transient double storage |
| **Quarantine rather than discard** | Drop failed data | A rising quarantine rate on one vehicle is a hardware fault signal, not noise | 90 days of storage for data that may be unusable |

### 1.5 How unreliable connectivity is handled

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Durable local buffer, store-and-forward** | Upload-on-generate | A cloud or link outage delays ingestion; it does not lose data. This is the single most important reliability property in the system, and it lives on the vehicle rather than in the cloud | Finite on-vehicle storage — see the priority queue in §1.1 |
| **Exponential backoff with jitter** | Fixed retry interval | Prevents an entire fleet reconnecting after an outage from arriving as a synchronised thundering herd | Slower recovery for an individual machine |
| **Idempotent retry** | Transactional upload protocol | See §1.2 — this is why retry is safe at all | — |
| **Physical media tier for prolonged blackouts** | Software-only solution | Days or weeks fully offline is an operational problem, not a software one. A technician swapping a drive is standard practice at remote sites | Logistics; higher latency to the platform |

### 1.6 How it scales as vehicles increase

Four axes, scaled independently:

| Axis | Absorbed by | What actually binds |
|---|---|---|
| More vehicles | S3 and the streaming layer scale without intervention; processing queues deepen | Not the cloud, at this volume |
| More data per vehicle | Storage lifecycle; the four transfer tiers | **Depot upload bandwidth** |
| More consumers and queries | Iceberg partitioning; serverless query concurrency | Query **cost** before query capacity |
| More vehicle variants | Per-variant schemas and bundles; the compatibility field already exists | Bench hardware for validation |

---

## 2 · Data selection and active learning

**The constraint.** 10,000 hours recorded against 100 hours that can be annotated.

> **The 100 hours is a stand-in for a ceiling, not a number the design depends on.** It will be a different figure next quarter, and as the fleet grows the recorded side grows far faster than the annotated side — so the fraction shrinks rather than holds. Nothing below is tuned to 100 hours: the ceiling is a single config value, the bucket shares and caps are proportions, and the scoring is independent of corpus size. What the design is actually built around is the permanent shape of the problem — **only a small part of what is recorded can ever be looked at, so the system must decide where that attention goes.**

The limit is financial rather than technical, and that is what makes it durable: more compute does not relieve it. So the question is never *how much can we annotate*, it is **how do we concentrate a fixed amount of human attention on the material that carries the most information.**

Random sampling fails that question on two counts. Most footage is a machine driving straight across a flat dry field, which the stack already handles — so a random hour buys almost nothing. And it **degrades over time**: as the model improves, the share of footage it already handles grows, so the expected value of a random hour falls every cycle. Selection therefore has to get smarter simply to hold its value constant, which is precisely why it is the component whose returns compound.

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **2.1 Four signals — WRONG, UNSURE, CONFLICT, RARE** | Classic uncertainty sampling | Uncertainty **cannot detect confident error** — the model 97% certain and wrong. That is the highest-risk failure mode, because the machine proceeds at full speed into it, and only WRONG and CONFLICT can see it. WRONG also needs no model at all, which solves the cold start | More scoring machinery |
| **2.2 Weighted linear score** | A learned ranking model | Every selection is explainable, and it operates from cycle one with no training data about selection itself | Weights hand-tuned initially; a learned ranker is a second-phase upgrade |
| **2.3 Quality as a multiplier, not an additive term** | Quality as a penalty added to the score | A faulty sensor produces high uncertainty *and* high cross-sensor conflict. Only a multiplier suppresses the clip regardless of how strongly it scores elsewhere | None significant |
| **2.4 Adaptive frame sampling** with three safety properties | Fixed-rate subsampling | (1) Sampling governs **scanning, not storage** — raw recordings stay complete. (2) Events are detected in **logs, not frames**, so skipping frames cannot conceal them. (3) The rate rises to full 30 fps inside event windows. Without these, a person stepping into the path for half a second could be sampled away | More complex sampling logic |
| **2.5 Three-group shortlist** — all events + all rare + random sample of ordinary | Rank by the cheap score and take the top N | At shortlist time only WRONG and RARE have been computed. Ranking on those admits almost exclusively event-bearing clips and **systematically excludes what UNSURE and CONFLICT exist to find** — the funnel becomes self-confirming | Larger shortlist, higher GPU cost at the scoring stage |
| **2.6 Diversity-attenuated greedy selection** over an ANN index | Pure ranked selection; clustering | One dusty afternoon produces hundreds of near-identical high-scoring clips. Ranking alone spends the budget on one afternoon. Each selection attenuates its near neighbours by ×0.3 | Requires an embedding index; clustering remains a simpler fallback |
| **2.7 Budget split 20% must-take / 70% scored-diverse / 10% random** | Fully scored selection | The random reservation preserves **evaluation validity** — if every labelled clip was chosen because the model struggled, normal-condition performance becomes unmeasurable — and is the only mechanism that can surface a failure mode no signal was designed to detect | 10% of the budget not optimised for information value |
| **2.8 15% per-vehicle cap** | Uncapped allocation | One machine with a dirty lens would otherwise consume the entire budget. The cap doubles as a fault detector: a vehicle repeatedly hitting it is a maintenance signal | May constrain a genuinely information-rich machine |
| **2.9 Clock-synchronisation gate on CONFLICT** | Trusting cross-sensor comparison | Below 10 ms the signal is trusted; above 50 ms it is disabled, because correctly functioning sensors appear to disagree on every frame when they are 200 ms apart | The signal is unavailable on poorly synchronised vehicles |
| **2.10 10-second clips** | Single frames; whole sessions | Matches annotator throughput and prevents intra-moment duplication | Marginally coarser selection granularity |

> **The point most likely to be challenged.** "Take the top 10% by score" is the intuitive shortlist, and it is wrong — the cheap signals available at that stage are not the signals you are trying to find. A filter that pre-selects for what you already know makes the expensive stage confirm rather than discover.

---

## 3 · Dataset and training pipeline

**What this stage produces is a *candidate*,** not a deployed model. Training answers *is this better*; deployment answers *is this safe to release*. Those are different questions with different evidence, and keeping them separate is what makes the gate in §4 meaningful.

### 3.1 Dataset creation and versioning

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **A dataset version is an immutable manifest of references**, written once | A folder of copied files | A folder is mutable. Someone removes a bad clip, corrects fifty labels, appends a batch — the name stays `v4` and *"what data produced this model"* becomes unanswerable. References keep versioning cheap enough that engineers actually create versions | Correctness depends on the immutable raw zone; content hashes are the detection mechanism |
| **Content hash per sample, verified at load** | Trusting the reference | If a referenced file ever changes, the run aborts rather than silently training on different data | Hash computation at build time |
| **Sampling weights, not duplication**, for class and scenario imbalance | Physically copying rare samples | Duplication makes the manifest misrepresent its own contents and corrupts every count derived from it | Sampler complexity |

### 3.2 Splits — the decision that silently destroys evaluation if it is wrong

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Session-level splits** | Random split over frames | Consecutive frames are near-duplicates. A random split puts one frame in training and its twin in test, and the score comes back **high, stable, and unrelated to field performance.** It does not present as an error; it presents as success | Less data-efficient; splits cannot be balanced precisely |
| **Permanently sticky assignment** — `hash(session_id)`, never re-drawn | Re-splitting each build | If splits are redrawn, last version's test data becomes this version's training data, and **every historical model comparison becomes invalid.** The loss is unrecoverable — the models cannot be re-measured against a split that no longer exists | A valuable session may land entirely in test |
| **Held-out sites and dates in the test split** | Same-distribution test split | Measures generalisation rather than interpolation. A new field, next month, is what deployment actually is | Test scores read lower than same-distribution scores |
| **An independent leakage check as its own pipeline step** | Trusting the split implementation | The rule can be satisfied exactly while leakage occurs: a session re-ingested under a new ID is one physical drive with two identifiers, hashed onto opposite sides. The check compares **content** — exact hashes plus near-duplicate embeddings — not identifiers | ANN index cost per dataset build |

### 3.3 Reproducible training

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Four pins: dataset hash · git SHA · container image digest · config and seeds** | Pinning code and data only | The environment pin is the one usually weakened. **An image tag is a mutable pointer** — `:latest` resolves differently over time, and CUDA, driver and library versions shift with no record in the run | Image management overhead |
| **Statistical, not bitwise, reproducibility — stated explicitly** | Deterministic GPU kernels | Bit-identical reproduction costs roughly 20–30% throughput for a property rarely needed. Claiming stronger reproducibility than has been paid for is worse than claiming none, because someone will rely on it | Re-runs vary within normal run-to-run variance |

### 3.4 Model evaluation

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **A frozen evaluation set**, refreshed quarterly and deliberately | A continuously extended set | A growing exam means successive models sat different tests and their scores are not comparable. Each refresh re-scores the current production model so a valid baseline survives | Drifts from the operating domain between refreshes |
| **Gate on per-slice metrics, not the aggregate** | A single aggregate score | A scenario that is 3% of the evaluation set contributes 3% of the aggregate, so a severe regression confined to it is invisible. **A real result from this design: +1.2 points overall, −5.7 in dust.** For a machine in a dry field that model is worse, and the aggregate hid it. The rare slices are exactly the costly ones | More evaluation compute; occasional noisy failures on small slices, managed by minimum slice sizes and tolerance bands |
| **A regression suite of real past field incidents**, which only grows | Slice metrics alone | Specific known failures must not return regardless of summary statistics. Entries are never removed, because the conditions that produced them have not stopped existing | Curation effort |

### 3.5 Experiment tracking

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Every run recorded automatically** — inputs, metrics, artifacts, lineage | Recording runs that seem important | A run that is not recorded did not happen. A pipeline permitting unrecorded runs accumulates models whose origin cannot be established | Storage for every failed run — which is the point; the dust failure was the most useful run of its cycle |
| **MLflow, self-hosted** | Weights & Biases (SaaS) | No per-seat cost, and field recordings and model artifacts remain inside the organisation's own account | Weaker interface, one more service to operate. Revisit past ~15 engineers |

### 3.6 Model and artifact management

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **The registry is a gate, not a store** — stages `candidate → validated → shadow → production → archived` | A model directory | Storage is object storage. What the registry adds is a **stage** and a **lineage record** tying a model to the exact data, code and environment that produced it | — |
| **Registration rejected without an attached evaluation report**, enforced in the API | A review checklist | A rule enforced by convention is a rule that holds until the first deadline | Marginally slower registration path |

### 3.7 Re-running when new data arrives

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Three triggers:** accumulation (+5% by volume), field performance, schedule | Retrain on every arrival | Retraining on fifty new clips burns GPU hours learning noise — but a serious field regression must not wait for a volume threshold. The performance trigger is **feedback edge ①** expressed as a mechanism | Latency between annotation and improvement, bypassed by the performance trigger when it matters |
| **A weekly scheduled floor** | Trigger-only execution | A pipeline that runs only when needed is a pipeline that is broken when needed | Occasional unnecessary runs |

### 3.8 Training throughput

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Sequential ~1 GB shards for training reads** | Per-sample object reads | One request per file starves the GPU — utilisation settles around 30% waiting on the network. The manifest stays authoritative; shards are a regenerable materialisation of it | Shard rebuild per dataset version |

---

## 4 · CI/CD and deployment

**The constraint.** Support continuous development while preventing an unvalidated model or software change from reaching a vehicle. The resolution is not to slow development down — it is to make the path to a vehicle **narrow and automatic**, so that speed is bounded by the gate rather than by caution.

**Four properties of the target decide most of what follows**, and none of them hold for a server:

| Property | Consequence |
|---|---|
| It can injure someone | A named human stays in the production approval path |
| It is offline for days at a time | Desired-state convergence, not push deployment |
| It cannot be recreated | Rollback must work with **no network and no human** |
| It is busy when the update arrives | The vehicle decides when to install, not the pipeline |

### 4.1 Software changes

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Replay against recorded field sessions in CI** | Synthetic fixtures only | Regression testing against the real distribution, catching behavioural divergence and latency regressions that no unit test produces. It is possible **only because the raw zone is immutable and complete** — a Task 1 decision made for unrelated reasons | Corpus curation; replay compute per commit |
| **A curated, versioned replay corpus that only grows** | Replaying everything, or a fixed sample | Scenario coverage from the taxonomy, plus every session associated with a past field incident | Storage pinned to instant-access tiers |
| **Images addressed by digest** | Image tags | Same reasoning as §3.3 | — |

### 4.2 ML and model changes

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **Re-evaluate the compiled artifact on target hardware** | Trusting the training-time evaluation | **The artifact that trains is not the artifact that runs.** It is exported, quantised and compiled for the vehicle's accelerator, and **quantisation degrades low-contrast inputs disproportionately** — exactly the rare, costly slices. In this design v7 passed dust at FP32 and failed it at INT8. Skip this step and the model you validated and the model you deployed are different objects, with the deployed one carrying a report saying it passed | An additional evaluation run per release |
| **Provenance verification before compilation** | Trusting the candidate's score | A candidate with incomplete lineage is rejected regardless of its metrics | — |

### 4.3 The release unit, and preventing unvalidated deployment

**"Validated" is given an operational definition** — seven conditions, all of which must hold before a bundle can be promoted.

```mermaid
graph TB
    B["bundle candidate"]
    C1["1 · every artifact traceable to source<br/>git SHA · image digest · dataset version · run id"]
    C2["2 · software: static, unit, integration pass"]
    C3["3 · replay: no behavioural or latency regression"]
    C4["4 · model: slices and regression suite pass<br/>ON THE COMPILED ARTIFACT, ON TARGET HARDWARE"]
    C5["5 · hardware-in-the-loop passed"]
    C6["6 · bundle manifest signed"]
    C7["7 · named human approved — recorded"]
    REL["RELEASABLE"]
    NO["blocked — recorded, not released"]

    B --> C1 --> C2 --> C3 --> C4 --> C5 --> C6 --> C7 --> REL
    C1 & C2 & C3 & C4 & C5 & C6 & C7 -.->|"any fails"| NO

    classDef auto fill:#eef4fb,stroke:#5b86b8,color:#13293d
    classDef human fill:#fff6e8,stroke:#d08a2e,color:#5c3a00
    classDef bad fill:#fbeaea,stroke:#c0392b,color:#7b241c
    classDef good fill:#eefaf0,stroke:#3f9c62,color:#14432a
    class C1,C2,C3,C4,C5,C6 auto
    class C7 human
    class NO bad
    class REL good
```

Conditions 1 to 6 are automatic. Condition 7 is deliberately not — and the reasoning is below.

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **The release unit is a bundle** — software image + compiled models + config + calibration schema + hardware target, signed as one | Deploying software and models independently | A model's accuracy depends on pre- and post-processing that live in the software. Change the normalisation constants or the NMS threshold and the model behaves differently **without the model changing.** A model validated against software v12 has no established behaviour under v13 | Couples release cadence — a one-line fix requires a full release and full validation |
| **A gate of seven conditions** — traceability, software tests, replay, compiled-model evaluation, hardware-in-the-loop, signature, named human approval | An approval checklist | This is the operational definition of "validated". Six are automatic; conditions 1–6 produce the evidence, and condition 7 records accountability | Hours of latency per release |
| **Hardware-in-the-loop before release** | Software testing only | **There is no staging server here — the staging environment for a robot is a physical machine.** Thermal throttling, memory pressure from the recording stack competing with perception, and embedded latency budgets cannot be reproduced off-target | Bench hardware per vehicle variant |
| **A named human approves production promotion** | Fully automated promotion | Auto-promotion is correct where failure is reversible and bounded. Here it is neither — the blast radius is physical machines near people. The approver is not re-deriving evidence; they are accountable, and the signature records that | Latency, which is not the binding constraint on a weekly cadence |

### 4.4 Enforcement, rollout and rollback

| Decision | Instead of | Why | Cost accepted |
|---|---|---|---|
| **The gate is enforced in the pipeline *and* on the vehicle** | Pipeline enforcement alone | The two fail independently. A pipeline can be bypassed with sufficient access; **a vehicle that refuses unsigned bundles cannot be made to accept one remotely.** The vehicle independently checks signature, hardware target, calibration schema and the revocation list | Key management; verification time at install |
| **Shadow before canary** | Canary directly | The candidate runs on live sensor data with its outputs logged and never actuated — real field evidence at **zero operational risk** | Compute, memory and thermal cost on a constrained device; time-boxed and auto-disabled if production headroom drops |
| **Shadow disagreements fed back into the selection pool** | Discarding them after validation | A frame on which two independently trained models disagree is difficult by construction. **Validating a model produces the data that improves the next one** — feedback edge ③ | Storage and scoring for disagreement clips |
| **Time-in-stage *and* metric thresholds at every transition** | Either alone | A metric threshold alone can be satisfied by two easy hours; a time threshold alone can be satisfied while metrics degrade | Roughly a week to reach the full fleet |
| **Dual-slot A/B with automatic revert on failed boot health check** | In-place update | Rollback works with **no network and no human** — which is exactly the state a bad bundle creates — and is bounded in minutes rather than waiting on a diagnosis | Doubles system storage on the device |
| **Download decoupled from installation** | Install on receipt | Installation proceeds only when parked, with sufficient power margin, no pending upload backlog, and the operator informed | The fleet is never instantaneously consistent, which the design accommodates rather than fights |
| **Bundle version recorded in every recording's session metadata** | Deployment logs only | **Data cannot be rolled back.** A defective model that ran six hours produced six hours of recordings. With this field, every artifact it produced is identifiable in one query; without it the contamination is permanent and undetectable | One metadata field |
| **A separate, bounded configuration path** — schema-validated, bounds-checked in CI and again on the vehicle | Everything is a bundle | Requiring a full release for a threshold change creates pressure to bypass the process, which produces **undocumented on-machine overrides — invisible, and strictly worse.** Anything the models were validated against is excluded from this path by schema | A second path that can break a vehicle |

---

## 5 · Cloud architecture

> **The scarcest resource is not compute or storage. It is engineering attention.**

At tens of machines, AWS absorbs this load almost regardless of how the architecture is drawn. What it cannot absorb is a few engineers operating a Kubernetes cluster, a Kafka cluster and a Spark cluster *while also* building the thing that differentiates the company.

Two rules follow: **buy managed unless managed forces a design compromise**, and **build only the selection and curation logic** — everything else is plumbing, and plumbing should be rented.

### 5.1 The services, and why each one

| Service | Chosen over | Why | Cost accepted |
|---|---|---|---|
| **IoT Greengrass** | A custom agent | Store-and-forward when disconnected, and remote deployment of the recording stack without physical access to a machine in a field | Tied to one vendor's agent on the vehicle |
| **IoT Core** | A self-run MQTT broker | One X.509 certificate per machine, and a device shadow that carries the desired bundle version — which is exactly the desired-state convergence deployment needs | Another managed service in the path |
| **Amazon MSK — Kafka** | A cloud-native managed queue | **Portability.** Some customer sites — mining especially — will have no dependable link to any cloud, and the streaming layer is the one component that must then run locally. Kafka runs anywhere | Brokers to size and patch, where a fully managed queue needs neither |
| **Glue Schema Registry** | Validating downstream, or not at all | A firmware change that adds a field or alters a unit is caught at ingest instead of surfacing weeks later as unexplained data | One more thing to register when a message shape changes |
| **Data Firehose** | A streaming Spark job | Buffering, file sizing and compaction into Iceberg, with no job to write, deploy or operate | Less control over the landing format |
| **S3** | A distributed filesystem | One substrate for every lifecycle state. **Object Lock** on `raw/` enforces immutability at the storage layer, which dataset manifests and replay testing both silently assume | Eventual consistency semantics to design around |
| **Iceberg + Glue Data Catalog** | Plain Parquet; Redshift | Schema evolution when a sensor is added, snapshot IDs so a dataset can record the catalog state it was built against, and ACID writes with no coordination layer to build | Compaction and snapshot expiry must actually run on a schedule |
| **RDS PostgreSQL** | Aurora Serverless; DynamoDB | The operational state is ~10⁶ rows at low transaction rates, joined constantly. Aurora's elasticity solves a problem this workload does not have; DynamoDB would trade a write-scale problem we do not have for a query-rigidity problem we would acquire | A fixed instance size to revisit later |
| **AWS Batch on EC2 Spot** | On-demand; a Kubernetes cluster | Every job is already idempotent and restartable, so interruption is cheap — roughly a two-thirds saving for a property the pipeline had to have anyway | Jobs must tolerate interruption |
| **Glue · Athena** | EMR; Redshift | Scheduled transforms and SQL over Iceberg with no cluster to own. EMR Serverless is the upgrade when job complexity outgrows Glue's abstractions | Less control than a Spark cluster |
| **SageMaker Training** | Self-managed GPU instances | Per-second billing, managed spot with checkpointing, and interruption handled by the service rather than by code the team maintains | Less control over the training environment |
| **MLflow, self-hosted** | Weights & Biases; SageMaker Model Registry | No per-seat cost, and field recordings and model artifacts stay inside the organisation's own account. Keeping the registry here too means a model's lineage lives in one system — lineage in two places is lineage nobody trusts | Weaker interface, one more service to run |
| **Step Functions** | Airflow for everything | Per-recording verification is thousands of short independent runs a day with branching. Billed per transition, so an idle week costs nothing | A second orchestrator to learn |
| **Airflow (MWAA)** | Step Functions for everything | The pipeline is dependency-rich and routinely re-run over historical ranges. Expressing a backfillable DAG as a state machine costs more in authoring pain than the service costs to run | A fixed monthly cost that does not shrink with usage |
| **EventBridge** | Point-to-point wiring | S3 events, schedules, fleet alarms and manual triggers all enter in one place | — |
| **GitHub Actions · ECR · AWS Signer** | CodePipeline | Better ecosystem, and OIDC removes long-lived credentials. Images addressed by digest; bundles signed with a key whose public half is on every vehicle | Replay testing has to reach AWS compute |
| **CloudWatch + SNS** | A third-party observability stack | Fleet inventory, runtime health and data-quality alarms in the account that already holds everything else | Weaker querying than a dedicated tool |

**Deliberately not used:** `EKS` — nobody should administer a cluster at this team size · `Redshift` — serverless query over Iceberg serves this volume with no cluster · `DynamoDB` — access patterns are relational · `Aurora` — elasticity this workload does not need · `SageMaker Pipelines` — a third orchestrator · `SageMaker Model Registry` — would split a model's lineage · `Lake Formation` — IAM and bucket policies suffice for one team · `Multi-region active-active` — disproportionate to the failure modes actually faced · `Managed Flink / Kafka Connect` — no stream-processing requirement exists.

### 5.2 The seven things the brief asks about

| | Approach |
|---|---|
| **Scalability** | Managed and serverless by default, so growth is a configuration change rather than a capacity project. The four axes — more machines, more data per machine, more queries, more vehicle variants — scale independently. §7 names what actually binds first, and it is not the cloud |
| **Reliability** | The vehicle is the first line: it buffers locally and forwards when connected, so a cloud outage delays ingestion rather than losing data — and nothing in AWS provides that. Containment is architectural rather than operational: idempotent keys, dead-letter queues, and a quarantine zone so bad data stops instead of propagating. Single region, with bundles and model artifacts copied to a second one so a regional failure cannot leave the fleet without a way to deploy |
| **Cost** | Storage dominates at every scale, and it grows with bytes retained rather than with machines — so the lever is deciding what to keep, not tuning jobs. That makes selection a cost lever as well as a quality one: the same mechanism that decides what is worth annotating decides what is worth keeping in instant-access storage |
| **Data storage** | One S3 substrate with prefixes by lifecycle state, Object Lock on raw, and automatic tiering since recordings are written once and read rarely. Two stores because the questions differ — Iceberg for search across billions of rows, PostgreSQL for transactional state |
| **Compute** | Spot by default for anything interruptible, which every job already is. Managed training rather than a cluster. One GPU at a time, because annotation throughput is the binding constraint by about an order of magnitude |
| **Security** | One certificate per machine, scoped so a vehicle can only write its own data. Separate KMS keys per data class. No long-lived credentials — SSO for people, OIDC for CI. And face and plate blurring on the annotation export, because machines in agriculture and construction record people and the exposure is largest where data leaves the account |
| **Automation** | Event-driven ingestion rather than scheduled sweeps, one event bus, and infrastructure as code throughout so `dev` and `prod` are the same definitions with different values |

## 6 · Implemented component

The **data selection and active-learning pipeline** is implemented as working code.

Chosen because it is the component whose returns compound, it is what the role description describes as the ideal candidate's work, it requires no infrastructure to demonstrate, and its scoring functions are deterministic and therefore genuinely testable.

Source, README, tests, and example input and output are in `3-implementation/`.

---

## 7 · What breaks first, and what comes next

**The cloud is not the constraint.** What binds first is physical and financial:

| Binds first | Response | Already addressed by |
|---|---|---|
| **Depot upload bandwidth** — a link serving 5 machines does not serve 50 | More aggressive on-vehicle reduction; the physical tier expands | §1.1 |
| **The annotation budget** — ten times the data, not ten times the budget | Selection carries more weight, which is its compounding argument | §2 |
| **Bench hardware for hardware-in-the-loop** — scales with vehicle *variants*, not fleet size | Per-variant benches; parallel compile-and-evaluate stages | §4.3 |

**Evolution path, in the order it should happen:**

| When | Change |
|---|---|
| Multiple verticals — agriculture, mining, construction | Per-variant bundles with an explicit hardware compatibility matrix. The field and the on-vehicle check already exist |
| Hand-tuned selection weights stop being obviously right | Replace the linear score with a learned ranker, trained on which selected clips actually improved the model |
| Annotation throughput becomes the ceiling | Expand model-assisted pre-labelling; auto-accept high-confidence pre-labels and route only uncertain ones to humans |
| Datasets outgrow single-node training time | Distributed data-parallel training — deliberately not built now |
| On-premises customer sites appear | Move the streaming layer to Kafka; everything else is already portable or S3-compatible |
| Team passes roughly 15 engineers | Revisit MLflow self-hosting, account structure, and fine-grained table access |

---

## 8 · Consolidated trade-off register

| # | Decision | Alternative | Cost accepted |
|---|---|---|---|
| 1 | Four-tier transfer, depot WiFi for bulk | Single upload path | Depends on daily depot return; physical media is the fallback |
| 2 | 60-second MCAP chunks | Whole-session files | More objects to track |
| 3 | On-vehicle ULIDs, idempotent keys | Server-assigned IDs | Larger keys; deterministic derivation required |
| 4 | Manifest sidecar *and* catalog | Catalog only | Two artifacts to keep in step |
| 5 | Calibration version mandatory at ingest | Assume calibration is stable | One more enforced field |
| 6 | Integrity hard-fails, quality soft-flags | One validation step | Two code paths |
| 7 | Immutable raw zone, promotion pattern | Write in place | Transient double storage |
| 8 | Iceberg for search, RDS PostgreSQL for state | One store; Aurora; DynamoDB | Two stores to operate |
| 9 | Four selection signals | Uncertainty sampling alone | More scoring machinery |
| 10 | Weighted linear score | Learned ranker | Weights hand-tuned initially |
| 11 | Quality as a multiplier | Quality as an additive penalty | None significant |
| 12 | Three-group shortlist | Top-N by cheap score | Larger shortlist, higher GPU cost |
| 13 | Diversity-attenuated greedy selection | Pure ranking; clustering | Requires an ANN index |
| 14 | 10% random reservation | Fully scored selection | 10% not optimised for information value |
| 15 | 15% per-vehicle cap | Uncapped allocation | May constrain a genuinely rich machine |
| 16 | Adaptive frame sampling | Fixed-rate subsampling | More complex sampling logic |
| 17 | Dataset as an immutable manifest of references | Materialised copies | Depends on the immutable raw zone |
| 18 | Session-level sticky splits | Random frame split | Less data-efficient; splits cannot be balanced |
| 19 | Held-out sites and dates in test | Same-distribution split | Test scores read lower |
| 20 | Independent leakage check | Trusting the split logic | ANN index cost per build |
| 21 | Frozen evaluation set | Continuously extended set | Drifts; scheduled refresh with baseline re-score |
| 22 | Gate on per-slice metrics | Aggregate metric only | More eval compute; noisy small slices |
| 23 | Regression suite of real incidents | Slice metrics alone | Curation effort; it only grows |
| 24 | Four pins, image by digest | Pinning code and data only | Image management overhead |
| 25 | Statistical reproducibility, stated | Bitwise determinism | Re-runs vary within variance |
| 26 | MLflow self-hosted | Weights & Biases | Weaker UI; one more service |
| 27 | Eval report required for registration, in the API | Review checklist | Slower registration path |
| 28 | Three retraining triggers | Retrain on every arrival | Latency before improvements land |
| 29 | Sequential shards for training reads | Per-sample object reads | Shard rebuild per version |
| 30 | Bundle as the release unit | Independent deploys | Couples release cadence |
| 31 | Re-evaluate the compiled artifact | Trust training evaluation | An extra evaluation per release |
| 32 | Hardware-in-the-loop before release | Software testing only | Bench hardware per variant |
| 33 | Gate in pipeline *and* on vehicle | Pipeline alone | Key management |
| 34 | Named human approval for production | Full automation | Hours of latency per release |
| 35 | Shadow before canary | Canary directly | On-device compute and thermal cost |
| 36 | Dual-slot A/B with automatic revert | In-place update | Doubled device storage |
| 37 | Download decoupled from installation | Install on receipt | Fleet never instantaneously consistent |
| 38 | Bundle version in session metadata | Deployment logs only | One metadata field |
| 39 | Separate configuration path | Everything is a bundle | A second path that can break a vehicle |
| 40 | Managed services by default | Self-operated | Less control |
| 41 | Kafka (MSK), two small brokers | A cloud-native managed queue | Brokers to size and patch; bought portability to on-prem sites |
| 42 | Two orchestrators, one rule | One orchestrator | Engineers must know which is which |
| 43 | Spot by default | On-demand | Jobs must tolerate interruption |
| 44 | Single region + selective replication | Multi-region active-active | Longer recovery from regional failure |
| 45 | Blur on export, full fidelity at rest | Blur at ingest | Raw zone holds personal data; must be governed |
| 46 | Single GPU, one training run | Distributed from day one | Revisit at scale; path documented |
| 47 | Glue Schema Registry on telemetry topics | Validate downstream, or not at all | One more thing to register per message-shape change |

---

## 9 · Three claims this design makes

**It is a flywheel, not a pipeline.** Three feedback edges are named and mechanised: field failures fire retraining, weak evaluation slices steer the next collection, and shadow-mode disagreements become annotation candidates. Remove them and this is a pipeline that is run repeatedly.

**Every gate fails closed.** No stage produces output by default. A label batch, a dataset version, a model candidate, a release bundle — each exists only because a specific check passed, and the failed attempt is recorded as completely as the successful one. The most useful run in the worked example was the one that failed.

**It is sized for this company, and it says where it stops.** Tens of machines now, low hundreds within three years. Every place where that assumption binds is named, along with the trigger that would change the decision — because an architecture that knows its own revision points is more useful than one that claims to be final.
