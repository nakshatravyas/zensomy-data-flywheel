# Technical Design - Data Flywheel for Autonomous Systems

**Nakshatra Vyas** · Data Engineer - Autonomous Systems · October 2026

**Deliverable 1** - a high-level architecture covering the complete Data Flywheel.
Decisions, assumptions and trade-offs are in [`2-design-document/`](../2-design-document/).

---

## 1 · The flywheel

A pipeline runs and stops. A flywheel stores momentum - each turn makes the next turn cheaper and more productive. **The feedback edges are the design.** Without them this is a data pipeline that happens to be run repeatedly.

```mermaid
graph LR
    V["VEHICLE<br/>sensors, recording"] --> I["INGEST<br/>Task 1"]
    I --> M["MANAGE<br/>Task 1"]
    M --> S["SELECT<br/>Task 2"]
    S --> A["ANNOTATE<br/>Task 3"]
    A --> D["DATASET<br/>Task 3"]
    D --> T["TRAIN<br/>Task 3"]
    T --> E["EVALUATE<br/>Task 3"]
    E --> VA["VALIDATE<br/>Task 4"]
    VA --> DE["DEPLOY<br/>Task 4"]
    DE --> V

    DE -.->|"① field failures<br/>fire retraining"| T
    E -.->|"② weak slices steer<br/>the next collection"| S
    VA -.->|"③ shadow-mode<br/>disagreements"| S

    classDef stage fill:#eef4fb,stroke:#5b86b8,stroke-width:1px,color:#13293d
    classDef fb fill:#fff6e8,stroke:#d08a2e,stroke-width:1px,color:#5c3a00
    class V,I,M,S,A,D,T,E stage
    class VA,DE fb
```

### The three feedback edges

| | Edge | Mechanism |
|---|---|---|
| ① | Field failures → retraining | A deployed model's slice-level failure rate crosses a threshold and triggers the pipeline that replaces it |
| ② | Weak evaluation slices → next collection | A slice that scores badly raises its weight in the next selection cycle |
| ③ | Shadow disagreements → selection pool | Frames where candidate and production models disagree are difficult by construction, and become annotation candidates |

### Why the returns compound rather than repeat

- As the model improves, the share of footage it already handles grows - so **the value of a randomly chosen hour falls every cycle.** Selection must get smarter simply to hold its value constant. That makes selection the component whose returns compound, not a cost measure bolted on.
- The production model pre-labels clips before annotation, so **a better model makes annotation cheaper** - the same budget buys more labelled hours each cycle.
- Every release contributes new regression tests, new replay sessions and new scenario weights. **The test suite strengthens as a by-product of shipping.**

---

## 2 · The system end to end

```mermaid
graph TB
    subgraph VEH["ON THE VEHICLE"]
        SEN["sensors<br/>camera · LiDAR · radar · GNSS/INS · CAN"]
        REC["recording stack<br/>ROS 2 → MCAP, 60-second chunks"]
        BUF["local buffer<br/>store-and-forward, priority queue"]
        SEN --> REC --> BUF
    end

    subgraph TRANSFER["FOUR TRANSFER TIERS"]
        T1["1 · cellular telemetry<br/>always, kilobytes/s"]
        T2["2 · cellular clips<br/>flagged events only"]
        T3["3 · depot WiFi<br/>bulk - about 98% of bytes"]
        T4["4 · physical media<br/>sites with no usable link"]
    end

    subgraph STORE["STORAGE"]
        LAND["landing/<br/>unverified"]
        RAW["raw/ - immutable, Object Lock"]
        QUAR["quarantine/"]
        CUR["curated/ - Iceberg catalog"]
    end

    GATE1{{"VERIFY<br/>integrity + quality"}}

    subgraph PIPE["FLYWHEEL STAGES"]
        SEL["SELECT<br/>10,000 h → 100 h"]
        ANN["ANNOTATE<br/>pre-labelled"]
        DSET["DATASET VERSION<br/>immutable manifest"]
        TRN["TRAIN<br/>four pins"]
        EVAL["EVALUATE<br/>aggregate + slices + regression"]
        CAND["MODEL CANDIDATE"]
        BUND["BUNDLE<br/>signed release"]
        ROLL["STAGED ROLLOUT<br/>shadow → canary → waves"]
        FLEET["FLEET"]
    end

    BUF --> T1 & T2 & T3 & T4
    T1 --> CUR
    T2 & T3 & T4 --> LAND
    LAND --> GATE1
    GATE1 -->|"pass"| RAW
    GATE1 -->|"fail"| QUAR
    RAW --> CUR
    CUR --> SEL --> ANN --> DSET --> TRN --> EVAL --> CAND --> BUND --> ROLL --> FLEET

    FLEET -.->|"field failures"| TRN
    EVAL -.->|"weak slices"| SEL
    ROLL -.->|"shadow disagreements"| SEL

    classDef gate fill:#fdecea,stroke:#c0392b,stroke-width:2px,color:#7b241c
    classDef store fill:#eef4fb,stroke:#5b86b8,color:#13293d
    classDef pipe fill:#eefaf0,stroke:#3f9c62,color:#14432a
    class GATE1 gate
    class LAND,RAW,QUAR,CUR store
    class SEL,ANN,DSET,TRN,EVAL,CAND,BUND,ROLL,FLEET pipe
```

### What each stage owes the next

| Stage | Produces | Guarantee it must hold |
|---|---|---|
| **Ingestion** | Verified, identified, catalogued recordings | Nothing in `raw/` is incomplete, unidentified or mutable |
| **Selection** | A ranked list of clip references | Nothing valuable was silently dropped; every choice is explainable |
| **Dataset** | An immutable manifest | The exact data behind any model is recoverable years later |
| **Training** | A model candidate plus an evaluation report | No candidate exists without evidence attached |
| **Deployment** | A signed, staged bundle | Nothing unvalidated reaches a machine |
| **Fleet** | Telemetry, failures, disagreements | The next cycle knows what to collect |

> Throughout this document, **a red node is a gate that fails closed.** No stage produces output by default; output exists only because a specific check passed.

---

## 3 · Data ingestion and management

**The constraint is arithmetic.** 400 GB per vehicle-day against a rural uplink is **178 hours of upload for 8 hours of driving**, and cellular is priced per gigabyte. Streaming everything to the cloud is not a rejected trade-off; it is impossible. The transfer architecture follows from that.

```mermaid
graph TB
    subgraph ONVEH["ON THE VEHICLE"]
        R["ROS 2 → MCAP<br/>60-second chunks"]
        MF["manifest per session<br/>chunk list + SHA-256 + counts"]
        ID["session id = ULID<br/>generated offline, sorts by time"]
        R --> MF --> ID
    end

    subgraph TIERS["TRANSFER, BY URGENCY AND SIZE"]
        A1["cellular telemetry"]
        A2["cellular flagged clips"]
        A3["depot WiFi bulk"]
        A4["physical media"]
    end

    L["s3://…/landing/<br/>unverified · expires after 7 days"]

    INT{{"INTEGRITY - hard fail<br/>manifest reconciliation<br/>SHA-256 · chunk count · sequence"}}
    QUAL{{"QUALITY - soft flag<br/>structural · temporal<br/>signal · semantic"}}

    RAWZ["s3://…/raw/<br/>immutable · Object Lock · canonical"]
    QZ["s3://…/quarantine/<br/>90 days for diagnosis"]

    subgraph CAT["CATALOG - two stores, two workloads"]
        ICE["Iceberg on S3 + Glue Catalog<br/>searchable metadata, about 10⁹ rows"]
        PG["PostgreSQL<br/>session state machine"]
    end

    ID --> A1 & A2 & A3 & A4
    A1 & A2 & A3 & A4 --> L
    L --> INT
    INT -->|"fail"| QZ
    INT -->|"pass"| QUAL
    QUAL -->|"flagged but usable"| RAWZ
    QUAL -->|"pass"| RAWZ
    RAWZ --> ICE
    RAWZ --> PG

    classDef gate fill:#fdecea,stroke:#c0392b,stroke-width:2px,color:#7b241c
    classDef store fill:#eef4fb,stroke:#5b86b8,color:#13293d
    class INT,QUAL gate
    class L,RAWZ,QZ,ICE,PG store
```

**Metadata is recorded at four levels** - fleet, vehicle, session, chunk - so fleet-wide facts are not repeated per chunk and chunk-level facts are not lost inside session summaries.

**Calibration version is a first-class required field.** A sensor mount that shifts two centimetres without re-calibration silently invalidates every LiDAR-to-camera projection from that moment onward. Nothing fails, and no error is raised.

---

## 4 · Data selection and active learning

**The constraint.** 10,000 hours recorded against 100 hours that can be annotated.

Everything below is therefore built around **the ratio and the mechanism**, never around a particular ceiling. The ceiling is one number in a config file; the question the design answers is **how to concentrate a fixed amount of human attention on the material that carries the most information**, whatever that amount turns out to be.

```mermaid
graph TB
    F["1.08 billion frames"]
    FS["ADAPTIVE FRAME SAMPLING<br/>1 frame / 2 s when idle<br/>full 30 fps inside event windows<br/>governs scanning only - raw stays complete"]
    C1["1.5 million clips of 10 s"]
    QF["quality filter<br/>exclude already-labelled"]
    C2["1.335 million clips"]
    SL["THREE-GROUP SHORTLIST<br/>all event-bearing<br/>+ all rare-scenario<br/>+ random sample of ordinary"]
    C3["133,000 clips"]
    SC["SCORE<br/>four weighted signals<br/>scaled by quality<br/>attenuated by similarity"]
    BU["BUDGET ALLOCATION<br/>20% must-take · 70% scored and<br/>diversity-attenuated · 10% random<br/>15% per-vehicle cap"]
    OUT["36,000 clips = the annotation ceiling<br/>100 h in this walkthrough"]

    F --> FS --> C1 --> QF --> C2 --> SL --> C3 --> SC --> BU --> OUT

    classDef step fill:#eefaf0,stroke:#3f9c62,color:#14432a
    classDef count fill:#eef4fb,stroke:#5b86b8,color:#13293d
    class FS,QF,SL,SC,BU step
    class F,C1,C2,C3,OUT count
```

### The four signals

```mermaid
graph LR
    subgraph EV["EVIDENCE OF DIFFICULTY - no ground truth required"]
        W["WRONG<br/>disengagement · emergency brake<br/>near-miss · re-plan storm<br/>needs no model"]
        U["UNSURE<br/>low confidence · narrow margin<br/>detection instability"]
        CF["CONFLICT<br/>camera and LiDAR disagree<br/>requires synchronised clocks"]
        RA["RARE<br/>coverage gap against<br/>the scenario taxonomy"]
    end
    SCORE["weighted score<br/>scaled by quality<br/>attenuated by similarity"]
    W -->|0.35| SCORE
    U -->|0.30| SCORE
    CF -->|0.20| SCORE
    RA -->|0.15| SCORE

    classDef sig fill:#eef4fb,stroke:#5b86b8,color:#13293d
    classDef out fill:#eefaf0,stroke:#3f9c62,color:#14432a
    class W,U,CF,RA sig
    class SCORE out
```

| Signal | Source | Available before a model exists |
|---|---|---|
| **WRONG** | Vehicle logs | ✅ Yes - the strongest signal needs no model |
| **UNSURE** | Model output | ❌ No |
| **CONFLICT** | Cross-sensor comparison | ⚠️ Partially - needs synchronised clocks |
| **RARE** | Catalog coverage counts | ✅ Yes |

Four signals rather than one because **uncertainty cannot detect confident error** - the model certain and wrong. That is the highest-risk failure mode, because the machine proceeds at full speed into it, and only WRONG and CONFLICT can see it.

### Worked ranking example

Eight representative clips from one selection cycle. This is the concrete output the pipeline produces: a ranked list with every term visible, so any selection can be explained.

> `score = (0.35·WRONG + 0.30·UNSURE + 0.20·CONFLICT + 0.15·RARE) × quality ÷ similarity`

| # | Clip | WRONG | UNSURE | CONFLICT | RARE | Qual | Sim | **Score** | Outcome |
|---|---|---|---|---|---|---|---|---|---|
| 1 | `veh03` disengagement, dust plume | 1.00 | 0.71 | 0.44 | 0.92 | 0.95 | 1.0 | **0.750** | **Must-take** |
| 2 | `veh01` emergency brake, low sun | 0.90 | 0.55 | 0.30 | 0.40 | 0.98 | 1.0 | **0.588** | Selected |
| 3 | `veh04` near-miss - LiDAR sees obstacle, camera does not | 0.80 | 0.12 | 0.78 | 0.55 | 0.93 | 1.0 | **0.516** | Selected |
| 4 | `veh02` wet descent, steep grade, no event | 0.00 | 0.48 | 0.10 | 0.95 | 1.00 | 1.0 | **0.307** | Selected - rare bucket |
| 5 | `veh03` same dust afternoon as #1, 90 s later | 1.00 | 0.68 | 0.41 | 0.92 | 0.95 | **2.4** | **0.310** | Deferred - diversity |
| 6 | `veh05` mud on lens, hardware fault confirmed | 0.60 | 0.88 | 0.91 | 0.30 | **0.21** | 1.0 | **0.147** | Rejected - quality |
| 7 | `veh01` straight-line travel, clear day | 0.00 | 0.08 | 0.05 | 0.05 | 1.00 | 1.0 | **0.042** | Not selected |
| 8 | `veh02` straight-line travel, clear day | 0.00 | 0.06 | 0.04 | 0.08 | 1.00 | 1.0 | **0.038** | Selected - random 10% |

**What each row demonstrates:**

- **#1** - A disengagement is the strongest available evidence: a trained operator judged the machine unsafe. It needs no model to detect and enters the must-take bucket unconditionally.
- **#3 - the confident error.** `UNSURE` is 0.12: the model is *certain*. Uncertainty sampling would discard this clip entirely. `WRONG` and `CONFLICT` are what surface it, and it is the most dangerous category in the set - the machine proceeds at full speed into a situation it has misread.
- **#5 - diversity attenuation.** Identical raw signals to #1, but a similarity divisor of 2.4 because near-neighbours were already selected. Without this term, one dusty afternoon consumes a large share of the budget. The clip is deferred, not discarded - it returns to the pool next cycle.
- **#6 - quality as a multiplier, not an additive term.** Every difficulty signal is high, but the sensor is faulty. Annotating it would teach the model about a dirty lens. A multiplier suppresses the clip regardless of how strongly it scores elsewhere; an additive penalty would not. The clip instead raises a maintenance alert.
- **#8 - the random reservation.** Scores below the threshold and is selected anyway, from the 10% random bucket. Without it, every labelled clip would be one the model struggled with, and performance under normal conditions would become unmeasurable.

---

## 5 · Dataset and training pipeline

**What this stage produces is a candidate**, not a deployed model. Training answers *is this better*; deployment answers *is this safe to release*.

Three questions have to be answered yes before a trained model is allowed to exist as a candidate: **are the labels good, is the test set clean, and is the model actually better.** Each one is a gate, and each gate stops the work rather than flagging it.

```mermaid
graph TB
    subgraph P1["① GET THE LABELS"]
        direction TB
        SEL["clips chosen in Task 2"]
        EXP["sent out for labelling<br/>the live model draws first"]
        IMP["labels come back"]
        QA{{"are the labels good?"}}
        REJ["back for re-labelling"]
    end

    subgraph P2["② BUILD THE DATASET"]
        direction TB
        BUILD["write a dataset version<br/>which clips, which labels, which split"]
        LEAK{{"any test clip<br/>also in training?"}}
        STOP["rebuild the dataset"]
    end

    subgraph P3["③ TRAIN AND CHECK"]
        direction TB
        TRAIN["train<br/>data, code, environment, seeds pinned"]
        EV["score it<br/>overall, per scenario, past failures"]
        CMP{{"better than<br/>what is live?"}}
        NOCAND["recorded, not released"]
        CAND["model candidate"]
    end

    T4["→ Task 4 decides whether<br/>it is allowed near a vehicle"]

    SEL --> EXP --> IMP --> QA
    QA -->|"no"| REJ
    QA -->|"yes"| BUILD --> LEAK
    LEAK -->|"overlap found"| STOP
    LEAK -->|"clean"| TRAIN --> EV --> CMP
    CMP -->|"no"| NOCAND
    CMP -->|"yes"| CAND --> T4

    classDef gate fill:#fdecea,stroke:#c0392b,stroke-width:2px,color:#7b241c
    classDef bad fill:#fbeaea,stroke:#c0392b,color:#7b241c
    classDef good fill:#eefaf0,stroke:#3f9c62,color:#14432a
    class QA,LEAK,CMP gate
    class REJ,STOP,NOCAND bad
    class CAND,T4 good
```

### The three gates, and why each one exists

| Gate | What it asks | Why it is there |
|---|---|---|
| **① Label quality** | Do two people labelling the same clip agree? | Labels are what the model learns from. Bad labels do not announce themselves later - they just become a model that is quietly wrong |
| **② Leakage** | Is any test clip also in the training set? | If it is, the score comes back high and means nothing. Checked by **content**, because the same drive re-ingested under a new name is one recording wearing two identities |
| **③ Comparison** | Is it better than the model in the field? | A model can gain overall and still get worse at night, or in dust. Those are the conditions that cost the most, so losing ground on any one of them counts as a loss |

Nothing proceeds by default. A failed run is recorded as completely as a successful one, so the reason a model did not ship is as traceable as the reason one did.

### Two decisions worth stating plainly

**Train and test are split by session, and the split never moves.** Frames a second apart are almost the same picture, so splitting frame by frame puts a clip in training and its near-twin in test - the score then looks excellent and says nothing about the field. Sessions are assigned once, by a hash of the session ID, and stay put. If splits were redrawn each time, last version's test data would become this version's training data, and every past model comparison would quietly become meaningless.

**Models are judged per scenario, not on one overall number.** A scenario that is a small share of the test set moves the overall score by a small amount, so a serious failure inside it is invisible in the headline. The rare scenarios are the expensive ones, which is exactly why they get their own pass or fail.

---

## 6 · CI/CD and deployment

**The constraint.** Ship continuously, while making it impossible for an unchecked model or an unchecked line of code to reach a machine in a field.

A vehicle is not a server, and four differences decide the whole design:

| The machine | So the pipeline must |
|---|---|
| can injure someone | keep a named person in the final approval |
| is offline for days | leave an instruction the machine collects, not push an update at it |
| cannot be recreated | make rollback work with no network and nobody present |
| is busy when the update arrives | let the machine choose when to install |

```mermaid
graph TB
    subgraph A["① WHAT CHANGED"]
        direction TB
        CM["code change"]
        CI["tests, then replay<br/>against real recorded drives"]
        MC["new model from Task 3"]
        CO["compile it for the vehicle's chip"]
        RE{{"does the compiled version<br/>still pass?"}}
        CM --> CI
        MC --> CO --> RE
    end

    subgraph B["② ONE SIGNED PACKAGE"]
        direction TB
        BUN["bundle<br/>software + models + config + calibration"]
        HIL{{"run it on real hardware"}}
        GATE{{"release gate<br/>7 checks, 6 automatic, 1 a person"}}
        BUN --> HIL --> GATE
    end

    subgraph C["③ ROLL OUT SLOWLY"]
        direction TB
        SH["shadow - 3 machines<br/>runs live, never acts"]
        CN["canary - 2 machines<br/>driving, supervised"]
        W1["a quarter of the fleet"]
        W2["the rest"]
        SH --> CN --> W1 --> W2
    end

    subgraph D["④ ON EACH MACHINE"]
        direction TB
        VEH["checks the bundle itself<br/>signature, hardware, calibration, not withdrawn"]
        INS["installs when parked<br/>and not mid-upload"]
        AB["will not boot?<br/>switches back by itself"]
        VEH --> INS --> AB
    end

    SELP["clips the two models disagreed on<br/>→ back to Task 2"]

    CI --> BUN
    RE --> BUN
    GATE --> SH
    W2 --> VEH
    SH -.->|"③ feedback edge"| SELP

    classDef gate fill:#fdecea,stroke:#c0392b,stroke-width:2px,color:#7b241c
    classDef stage fill:#eefaf0,stroke:#3f9c62,color:#14432a
    classDef box fill:#eef4fb,stroke:#5b86b8,color:#13293d
    class RE,HIL,GATE gate
    class SH,CN,W1,W2 stage
    class BUN,VEH,INS,AB,SELP box
```

### The four ideas in that picture

**① One package, never a loose model.** A model's accuracy depends on code that sits around it - how the image is prepared, what threshold filters the results. Change that code and the model behaves differently without the model changing. Ship them separately and combinations end up in the field that nobody ever tested together.

**② The model that trains is not the model that runs.** It gets shrunk to run on a small chip, and shrinking it costs accuracy - most of all on dim, low-contrast scenes, which are exactly the dust and night clips that matter. So the shrunk version is scored again, on the real hardware, before it counts.

**③ The gate is checked twice.** Once in the pipeline, and again by the machine before it installs anything. A pipeline can be bypassed by someone with enough access. A machine that refuses unsigned bundles cannot be talked into accepting one.

**④ Rollout buys evidence, and so does failure.** Shadow runs the new model on live sensors with its decisions recorded but never acted on - real evidence at no risk. Every frame where the new and old models disagreed is a hard frame by definition, and goes back into the pool worth labelling. **Validating a model produces the data that improves the next one.**

Each stage needs both a time threshold and a metric threshold before it promotes. Time alone can pass while the numbers slide; metrics alone can be satisfied by two easy hours in good weather.

### The one thing that cannot be rolled back

A bad bundle can be withdrawn, but the six hours it ran already produced six hours of recordings. So **every recording stores the bundle version that made it.** Withdraw a bundle and one query finds everything it touched. Without that field the contamination is permanent and invisible.

---

## 7 · Cloud architecture

The major services, and how they interact. The organising split: a **data plane** that bytes flow through, and a **control plane** that decides when things run.

```mermaid
graph LR
    subgraph L1["① VEHICLE"]
        direction TB
        GG["IoT Greengrass<br/>buffer<br/>store-and-forward"]
    end

    subgraph L2["② INGEST"]
        direction TB
        IOT["IoT Core<br/>device identity · MQTT"]
        MSK["Amazon MSK - Kafka<br/>runs on-prem unchanged"]
        FH["Data Firehose<br/>Kafka → Iceberg"]
        UP["presigned upload<br/>recordings direct to S3"]
    end

    subgraph L3["③ STORE - S3"]
        direction TB
        LAND["landing/<br/>unverified"]
        RAW["raw/ · Object Lock<br/>immutable"]
        CUR["curated/<br/>Iceberg tables"]
        ART["datasets<br/>models · bundles"]
    end

    subgraph L4["④ PROCESS"]
        direction TB
        BAT["AWS Batch on Spot<br/>parse · frames<br/>embeddings"]
        GLU["Glue + Athena<br/>transforms · SQL"]
    end

    subgraph L5["⑤ TRAIN"]
        direction TB
        SEL["selection"]
        SM["SageMaker Training<br/>+ evaluate"]
        CMP["compile for target<br/>then re-evaluate"]
        MLF["MLflow<br/>tracking + registry"]
    end

    subgraph L6["⑥ DELIVER"]
        direction TB
        BLD["GitHub Actions + ECR<br/>build · test · sign"]
        JOB["IoT Jobs<br/>shadow → canary → waves"]
    end

    subgraph CP["CONTROL PLANE"]
        direction TB
        EVB["EventBridge"]
        SFN["Step Functions<br/>verify each recording"]
        AF["Airflow<br/>the pipeline DAGs"]
    end

    subgraph SH["SHARED"]
        direction TB
        GDC[("Glue Data Catalog")]
        PG[("RDS PostgreSQL<br/>session state")]
        CW["CloudWatch + SNS"]
    end

    GG -->|"small"| IOT --> MSK --> FH --> CUR
    GG -->|"large"| UP --> LAND --> RAW --> BAT --> CUR
    GLU --> CUR --> GDC
    CUR --> SEL --> ART --> SM --> CMP --> ART
    SM --> MLF
    BLD --> ART --> JOB --> IOT --> CW

    EVB -.-> SFN -.-> LAND
    SFN -.-> PG
    AF -.-> SEL
    AF -.-> GLU
    CW -.->|"① field failures"| AF
    CMP -.->|"② weak slices"| SEL
    JOB -.->|"③ shadow disagreements"| SEL

    classDef veh fill:#fff4e6,stroke:#d08a2e,stroke-width:1.5px,color:#5c3a00
    classDef ing fill:#eaf3fc,stroke:#5b86b8,stroke-width:1.5px,color:#13293d
    classDef sto fill:#eef7f0,stroke:#3f9c62,stroke-width:1.5px,color:#14432a
    classDef prc fill:#f4eefb,stroke:#8a63b8,stroke-width:1.5px,color:#2e1a46
    classDef mlr fill:#fdeef0,stroke:#c0617a,stroke-width:1.5px,color:#4a1526
    classDef dlv fill:#fdf3e3,stroke:#b8862e,stroke-width:1.5px,color:#4a3310
    classDef ctl fill:#eceef5,stroke:#55607a,stroke-width:2px,color:#20283d
    classDef shr fill:#f2f4f7,stroke:#6b7785,stroke-width:1.5px,color:#2b3440
    class GG veh
    class IOT,MSK,FH,UP ing
    class LAND,RAW,CUR,ART sto
    class BAT,GLU prc
    class SEL,SM,CMP,MLF mlr
    class BLD,JOB dlv
    class EVB,SFN,AF ctl
    class GDC,PG,CW shr
```

**Solid lines are data. Dotted lines are decisions.** The three numbered dotted edges are the flywheel - the only paths that carry information backwards.

### How the pieces interact

| | What passes | Why it works that way |
|---|---|---|
| Vehicle → IoT Core → Kafka | Telemetry and events, kilobytes | Small and frequent. Needs ordering, replay, several independent consumers |
| Vehicle → S3 directly | Recordings, gigabytes | A 10 GB file never enters a message bus, and never touches compute we operate |
| Kafka → Firehose → Iceberg | Validated messages | Managed landing - no streaming job to write or run |
| S3 event → EventBridge → Step Functions | A reference, not a payload | Verification starts when data arrives, not on a schedule |
| Step Functions → `raw/` or `quarantine/` | A promotion decision | A partial upload never becomes canonical data |
| Airflow → selection → dataset → training | Clip IDs, then a manifest | Dependency-rich and periodically backfilled - DAG-shaped work |
| Training → compile → bundle → IoT Jobs | A signed release | What reaches a vehicle is one versioned unit |
| Fleet → CloudWatch → Airflow | Slice failure rates | The deployed model's own failures trigger its replacement |

### What each service is for

| Service | Doing what |
|---|---|
| **IoT Greengrass** | Buffers on the machine, forwards when connected, deploys the recording stack |
| **IoT Core** | One certificate per machine; carries the desired bundle version |
| **Amazon MSK - Kafka** | Telemetry and events. Chosen because it also runs at a site with no cloud link |
| **Data Firehose** | Reads Kafka, writes Iceberg. No streaming job to operate |
| **S3** | One storage substrate. `raw/` is write-once under Object Lock |
| **Glue Data Catalog** | Metastore for the Iceberg tables |
| **RDS PostgreSQL** | Session state, upload progress, fleet inventory |
| **AWS Batch on Spot** | Heavy work - parsing, frame extraction, GPU embeddings |
| **Glue · Athena** | Scheduled transforms, table maintenance, SQL with no cluster |
| **SageMaker Training** | Managed spot training with checkpointing |
| **MLflow** | Experiment tracking and the model registry |
| **GitHub Actions · ECR · Signer** | Build, test, replay, sign the bundle |
| **IoT Jobs** | Staged rollout, against the version each machine reports |
| **EventBridge** | One bus - S3 events, schedules, alarms, manual triggers |
| **Step Functions** | Per-recording verification: thousands of short runs a day |
| **Airflow** | The pipeline DAGs: selection, dataset build, train, evaluate, register |
| **CloudWatch + SNS** | Fleet inventory, data-quality alarms, the retraining trigger |

## 8 · Implemented component

The **data selection and active-learning pipeline** - section 4 of this document, as working code. Scoring, diversity-aware ranking and budget-constrained selection, with deterministic tests and example input and output.

See [`3-implementation/`](../3-implementation/).
