---
hide:
  - navigation
---

# Data Flywheel for Autonomous Systems

<p class="lede">A continuous loop that turns field data from off-road autonomous machines into measurably better models - and sends the machines back out to collect what the models still get wrong.</p>

<p class="byline"><strong>Nakshatra Vyas</strong> · Data Engineer - Autonomous Systems · October 2026<br>
Technical assessment · Zensomy Autonomous Technologies</p>

---

## The loop

```mermaid
graph LR
    V["VEHICLE<br/>sensors, recording"] --> I["INGEST"]
    I --> M["MANAGE"]
    M --> S["SELECT"]
    S --> A["ANNOTATE"]
    A --> D["DATASET"]
    D --> T["TRAIN"]
    T --> E["EVALUATE"]
    E --> VA["VALIDATE"]
    VA --> DE["DEPLOY"]
    DE --> V

    DE -.->|"① field failures<br/>fire retraining"| T
    E -.->|"② weak slices steer<br/>the next collection"| S
    VA -.->|"③ shadow-mode<br/>disagreements"| S

    classDef stage fill:#eef4fb,stroke:#5b86b8,stroke-width:1px,color:#13293d
    classDef fb fill:#fff6e8,stroke:#d08a2e,stroke-width:1px,color:#5c3a00
    class V,I,M,S,A,D,T,E stage
    class VA,DE fb
```

A pipeline runs and stops. A flywheel stores momentum - each turn makes the next turn cheaper and more productive. **The three dotted edges are the design.** Without them this is a data pipeline that happens to be run repeatedly.

---

## Where to start

<div class="grid cards" markdown>

-   :material-sitemap:{ .lg .middle } **Technical Design**

    ---

    How the system is built, start to finish. How data leaves the machine and arrives
    intact. How the system picks which footage is worth a human's time. How a dataset
    becomes a trained model, how that model is checked, and how it reaches a machine
    in the field. Mostly diagrams.

    [:octicons-arrow-right-24: Read it](technical-design.md)

-   :material-scale-balance:{ .lg .middle } **Design Document**

    ---

    Why it is built that way. Each choice, what was chosen instead, and what that
    choice costs. Opens with a table showing where every part of the brief is
    answered, and ends with every trade-off in one list.

    [:octicons-arrow-right-24: Read it](design-document.md)

</div>

<p class="footnote">Built with MkDocs Material. Diagrams are Mermaid, rendered from the same Markdown that is submitted.</p>
