# Paper Agent — Implementation Architecture

> **Stack:** Streamlit (UI), LangGraph (agent orchestration), LangChain (LLM abstraction), local filesystem (storage).
> **Principle:** No external databases, no cloud services, no vector stores. Everything is a file in a directory.

---

## 1. Directory Structure

```
~/.paper-agent/                    # Root — system-level, not per-project
├── config.yaml                    # LLM provider, API keys, defaults
├── projects/                      # One subdirectory per project context
│   └── gemma-s2s/                 # Example: your Gemma speech-to-speech project
│       ├── context.md             # Project Context Card (editable by user + agent)
│       ├── decisions.md           # Decision log: locked-in + open decisions
│       ├── knowledge.md           # Concepts the user has been exposed to
│       └── library/               # All ingested papers for this project
│           └── moshi-2024/
│               ├── metadata.yaml  # Paper title, authors, URL, ingestion date
│               ├── triage.md      # The 8-question Triage Report
│               ├── anatomy.md     # Architecture diagram description, loss fn, shapes
│               ├── action.md      # Verdict + action plan + trigger conditions
│               └── notes.md       # User's own notes (optional, user-edited)
├── archive/                       # Papers marked "Ignore" (kept for dedup)
└── templates/                     # Jinja2/Markdown templates for reports
```

**Why files instead of a database:**
- Markdown is grep-able, diff-able, and Git-trackable
- No migration headaches
- The "library" of 50 papers is still tiny by filesystem standards
- Templates can be shipped with the agent and version-controlled

---

## 2. LangGraph Workflow Design

The agent has two main workflows. Each maps cleanly to a LangGraph state graph.

### 2.1 Primary Workflow: Paper Ingestion

This is the full 4-stage triage pipeline. The graph has conditional edges — a paper can exit early at Stage 1 or 2 if it's clearly irrelevant.

```
                    ┌─────────────┐
                    │  PAPER IN   │
                    │ (PDF path)  │
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │  EXTRACT    │ ◄── Parse PDF: text, figures, tables
                    │  (parse)    │     Output: RawPaper object
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │  STAGE 1    │ ◄── Screener: compare abstract+intro
                    │  (screen)   │     against Project Context Card
                    └─────┬───────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
         RELEVANT    IRRELEVANT   PARADIGM_SHIFT
              │           │           │
              │     ┌─────▼───┐       │
              │     │ ARCHIVE │       │
              │     │ (exit)  │       │
              │     └─────────┘       │
              │                       │
              └───────────┬───────────┘
                          │
                    ┌─────▼───────┐
                    │  STAGE 2    │ ◄── Structural anatomy:
                    │  (anatomy)  │     extract figures, tables, loss eqns
                    └─────┬───────┘
                          │
              ┌───────────┼───────────┐
              │           │           │
          USEFUL      MARGINAL      IRRELEVANT
              │           │           │
              │     ┌─────▼───┐       │
              │     │SKIP TO │       │
              │     │VERDICT │       │
              │     └─────┬───┘       │
              │           │           │
              └───────────┬───────────┘
                          │
                    ┌─────▼───────┐
                    │  STAGE 3    │ ◄── 8-question Triage Report
                    │  (extract)  │
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │  STAGE 4    │ ◄── Skeptic's pass (limitations)
                    │  (skeptic)  │
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │ TRANSFORM   │ ◄── Math→pseudocode, resources→feasibility
                    │ (transform) │
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │   VERDICT   │ ◄── Implement / Monitor / Read-Deeper / Ignore
                    │  + ACTION   │     + trigger conditions
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │   WRITE     │ ◄── Persist all outputs to ~/.paper-agent/
                    │  (persist)  │
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │  UI UPDATE  │ ◄── Streamlit rerender
                    └─────────────┘
```

**LangGraph implementation notes:**
- Each node is a function that takes `AgentState` and returns `AgentState`
- `AgentState` is a typed dict carrying: `paper_id`, `project_id`, `raw_paper`, `screener_result`, `anatomy`, `triage_report`, `verdict`, `action_plan`
- Conditional edges check `screener_result.relevance` and `anatomy.usefulness` to route early exits
- The LLM is called inside each node via LangChain's ChatModel interface (provider-agnostic — works with Anthropic, OpenAI, or local models)

### 2.2 Secondary Workflow: Cross-Paper Query

Once papers are in the library, the user can ask comparative questions.

```
                    ┌─────────────┐
                    │   QUERY     │
                    │ (user asks) │
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │   LOAD      │ ◄── Load all triage reports + metadata
                    │  (library)  │     for the active project
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │   MATCH     │ ◄── Find papers relevant to the query
                    │  (retrieve) │     (keyword + semantic matching on reports)
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │  COMPARE    │ ◄── LLM compares matched papers
                    │  (analyze)  │     Produces structured diff
                    └─────┬───────┘
                          │
                    ┌─────▼───────┐
                    │  RESPOND    │
                    └─────────────┘
```

---

## 3. Streamlit UI Layout

### 3.1 Main View (Library + Ingest)

```
┌─────────────────────────────────────────────────────────┐
│  📚 Paper Agent                          [Project: gemma-s2s ▼]  │
├─────────────────────────────────────────────────────────┤
│                                                         │
│  ┌─────────────────┐   ┌──────────────────────────────┐ │
│  │                 │   │                              │ │
│  │  Drop PDF here  │   │  Library (12 papers)          │ │
│  │  or click to    │   │                              │ │
│  │  upload         │   │  ⬛ Implement: 2              │ │
│  │                 │   │  🟨 Monitor:   5              │ │
│  │                 │   │  🟦 Read:      3              │ │
│  │                 │   │  ⬜ Ignore:    2              │ │
│  └─────────────────┘   │                              │ │
│                         │  [Search...]  [Filter ▼]     │ │
│  ┌──────────────────────┤                              │ │
│  │ Quick actions        │  ┌────────────────────────┐  │ │
│  │ [Update Context]     │  │ Moshi (2024)            │  │ │
│  │ [Cross-paper query]  │  │ Verdict: IMPLEMENT      │  │ │
│  │ [Export library]     │  │ Ingested: 2026-05-08    │  │ │
│  └──────────────────────┘  │ Tags: streaming, mimi,   │  │ │
│                              │        full-duplex      │  │ │
│                              └────────────────────────┘  │ │
│                              ┌────────────────────────┐  │ │
│                              │ Mini-Omni (2024)        │  │ │
│                              │ Verdict: IMPLEMENT      │  │ │
│                              │ ...                     │  │ │
│                              └────────────────────────┘  │ │
└─────────────────────────────────────────────────────────┘
```

### 3.2 Paper Detail View (after clicking a paper in the library)

```
┌─────────────────────────────────────────────────────────┐
│  ← Back to Library                                       │
│                                                         │
│  Moshi: A Speech-Text Foundation Model...   [arxiv.org]  │
│  Défossez et al., 2024                                   │
│                                                         │
│  Verdict: 🟩 IMPLEMENT NOW                               │
│  ─────────────────────────────────────────               │
│                                                         │
│  [Triage Report] [Anatomy] [Action Plan] [Raw] [Notes]   │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ ## 1. I/O Signature                                  │ │
│  │                                                      │ │
│  │ **Input:** 24 kHz mono audio (user), streamed in      │ │
│  │ 80ms chunks via Mimi encoder → discrete tokens       │ │
│  │ at 12.5 Hz frame rate                                │ │
│  │                                                      │ │
│  │ **Output:** 24 kHz mono audio (Moshi), generated as   │ │
│  │ Mimi tokens → decoded to waveform in 80ms chunks     │ │
│  │                                                      │ │
│  │ **Internal:** Text tokens (inner monologue)           │ │
│  │ predicted as prefix to audio tokens per frame        │ │
│  │                                                      │ │
│  │ ## 2. Novelty                                        │ │
│  │                                                      │ │
│  │ First full-duplex speech-to-speech model with...     │ │
│  │ [continues...]                                       │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

The tab bar switches between the Triage Report, Anatomy (diagram descriptions + loss functions), Action Plan, raw extracted text, and user notes.

### 3.3 Ingestion Progress View (shown during active ingestion)

When a PDF is dropped, show a live progress indicator:

```
┌─────────────────────────────────────────────────────────┐
│  Ingesting: moshi_paper.pdf                              │
│                                                         │
│  ✅ PDF extracted (14 pages, 6 figures, 4 tables)       │
│  ✅ Stage 1: Screener → RELEVANT (urgency: HIGH)        │
│  ⏳ Stage 2: Extracting architecture...                  │
│  ⬜ Stage 3: Triage Report                               │
│  ⬜ Stage 4: Skeptic's Pass                              │
│  ⬜ Transformations                                      │
│  ⬜ Verdict + Action Plan                                │
│                                                         │
│  [Cancel]                                                │
└─────────────────────────────────────────────────────────┘
```

### 3.4 Cross-Paper Query View

```
┌─────────────────────────────────────────────────────────┐
│  Cross-Paper Query                                       │
│                                                         │
│  Ask: "How does the latency of Moshi compare to          │
│        Mini-Omni and LLaMA-Omni?"                        │
│                                                         │
│  ┌─────────────────────────────────────────────────────┐ │
│  │ Comparing 3 papers...                                │ │
│  │                                                      │ │
│  │ | Metric       | Moshi    | Mini-Omni | LLaMA-Omni | │ │
│  │ |--------------|----------|-----------|------------| │ │
│  │ | TTFAF (ms)   | 160      | 300       | 250        | │ │
│  │ | Frame rate   | 12.5 Hz  | 25 Hz     | 25 Hz      | │ │
│  │ | Codec        | Mimi     | EnCodec   | EnCodec    | │ │
│  │ | Full-duplex  | Yes      | No        | No         | │ │
│  │ | Backbone     | 7B       | 0.5B      | 7B         | │ │
│  │                                                      │ │
│  │ Key difference: Moshi's lower TTFAF comes from       │ │
│  │ streaming Mimi + Depth/Temporal transformer split.   │ │
│  │ Mini-Omni is simpler but not full-duplex.            │ │
│  └─────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────┘
```

---

## 4. Core Data Structures

### 4.1 Project Context Card (`context.md`)

```yaml
# ~/.paper-agent/projects/gemma-s2s/context.md
---
project: Extend Gemma 4 E2B for speech-to-speech
phase: literature_survey
milestone: Week 1 — Literature survey
constraints:
  gpu: "Single A100 40GB (early), 4-8× A100 (later)"
  latency_target_ms: 500
  languages: ["en"]
open_decisions:
  - "Codec: Mimi vs EnCodec"
  - "Single-stream vs multi-stream"
locked_decisions:
  - "Backbone: Gemma 4 E2B (frozen)"
  - "Training: LoRA + speech head"
  - "Framework: PyTorch + HF transformers"
pain_points: []
paper_count: 0
---
```

### 4.2 Paper Metadata (`metadata.yaml`)

```yaml
# ~/.paper-agent/projects/gemma-s2s/library/moshi-2024/metadata.yaml
paper_id: moshi-2024
title: "Moshi: A Speech-Text Foundation Model for Real-Time Dialogue"
authors: ["Alexandre Défossez", "..."]
year: 2024
url: https://arxiv.org/abs/2410.00037
code_url: https://github.com/kyutai-labs/moshi
ingested: 2026-05-09
tags: [streaming, full-duplex, mimi, inner-monologue, multi-stream]
verdict: implement
verdict_confidence: high
trigger_condition: null  # only for "monitor" papers
```

### 4.3 Agent State (LangGraph)

```python
from typing import TypedDict, Literal, Optional

class ScreenerResult(TypedDict):
    relevance: Literal["relevant", "irrelevant", "paradigm_shift"]
    urgency: Literal["high", "medium", "low"]
    reason: str  # one sentence why

class Anatomy(TypedDict):
    architecture_blocks: list[str]
    tensor_shapes: dict[str, str]
    loss_functions: list[str]
    key_tables: list[str]  # descriptions of important tables
    figures_described: list[str]

class TriageReport(TypedDict):
    io_signature: str
    novelty: str  # max 2 sentences
    cost_estimate: str  # translated to user's constraints
    baselines_beaten: str
    baselines_missing: str
    ablations_that_mattered: str
    failure_modes: str
    integration_difficulty: str

class ActionPlan(TypedDict):
    verdict: Literal["implement", "monitor", "read_deeper", "ignore"]
    summary: str  # one paragraph
    concrete_steps: list[str]
    trigger_condition: Optional[str]
    scoped_reading: Optional[str]  # for "read_deeper"

class AgentState(TypedDict):
    paper_id: str
    project_id: str
    pdf_path: str
    raw_text: str
    figures: list[str]  # base64-encoded or file paths
    screener: Optional[ScreenerResult]
    anatomy: Optional[Anatomy]
    triage: Optional[TriageReport]
    limitations: Optional[str]
    transformations: dict  # pseudocode, feasibility, roadmap
    verdict: Optional[ActionPlan]
    error: Optional[str]
    current_stage: str
```

---

## 5. PDF Handling Strategy

This is the hardest technical piece. ML papers are visually dense — architecture diagrams, loss function equations, and results tables are often the most important content, and plain text extraction loses them.

### Approach: Multi-Modal Extraction

```
PDF
 │
 ├──→ pdfplumber / pymupdf ──→ Plain text (for prose)
 │
 ├──→ pdf2image ──→ Page images ──→ Vision LLM
 │     (one image per page)         (describe figures, tables, equations)
 │
 └──→ camelot / tabula ──→ Structured table data
       (if tables are extractable)
```

1. **Text layer:** Use `pymupdf` (fitz) or `pdfplumber` to extract the text stream. This gives you the prose, section headings, and often inline math as LaTeX.
2. **Visual layer:** Convert each page to an image (300 DPI). Pass page images to a vision-capable LLM (Claude, GPT-4V, or Gemini) with a targeted prompt: "Describe every architecture diagram on this page. For each, list the components, their connections, and any tensor shapes or dimensions shown. Describe every table, preserving all numbers. Transcribe any equations."
3. **Table extraction:** If the PDF has selectable tables, `camelot` or `pdfplumber` can extract them as DataFrames. This is more reliable than asking a vision LLM to transcribe numbers.

**Trade-off:** The vision LLM call is the most expensive step (1 image per page × ~$0.01–0.05 per image). For a 12-page paper, that's ~$0.12–0.60. Acceptable. For a user on a budget: make this optional, with a "fast mode" that skips figures and just works from extracted text.

### Figure Storage

Extracted figure images are saved alongside the paper:
```
library/moshi-2024/
├── figures/
│   ├── page_3_arch.png      # Architecture diagram
│   ├── page_6_results.png   # Results table (as image)
│   └── page_8_ablation.png  # Ablation table
```

---

## 6. LLM Prompt Design (Node-Level)

Each LangGraph node has a specific prompt. These should be version-controlled.

### Stage 1: Screener Prompt

```
You are an ML engineer screening a research paper for a specific project.

PROJECT CONTEXT:
{project_context_card}

PAPER:
Title: {title}
Abstract: {abstract}
Introduction: {introduction}

Answer these three questions:
1. Does this paper touch the project's problem domain? (yes/no, one sentence why)
2. Does it provide a capability the project doesn't already have? (yes/no)
3. Is the claimed improvement large enough to change a decision in the project? (yes/no)

Then give:
- Relevance: relevant / irrelevant / paradigm_shift
- Urgency: high / medium / low
- Reason: one sentence

A "paradigm_shift" means: this paper changes the fundamental assumptions of the project. Flag this only if the paper makes a claim that, if true, would obsolete the current approach.
```

### Stage 2: Anatomy Prompt

```
You are analyzing the STRUCTURE of this paper — not evaluating it.

Given the full paper text, extract:

1. ARCHITECTURE: Describe the system as a block diagram in text form.
   - List every component/module
   - What connects to what
   - Tensor shapes at each boundary (if specified)
   - What is the backbone? What modules are added/replaced?

2. LOSS FUNCTIONS: List every loss function mentioned.
   - Equation number
   - What it optimizes
   - Any hyperparameters (λ, β, α) and their values

3. KEY TABLES: For each results table, note:
   - What metrics are reported
   - What baselines are compared
   - The rough magnitude of the improvement
   - Whether error bars / statistical tests are reported

4. ABLATIONS: List every ablation study.
   - What was varied
   - What was measured
   - Which variations mattered most

DO NOT summarize the paper. DO NOT evaluate quality. Only extract structure.
```

### Stage 3: Triage Report Prompt

```
You are producing an ENGINEERING TRIAGE REPORT for a specific project.

PROJECT CONTEXT:
{project_context_card}

PAPER ANATOMY (from Stage 2):
{anatomy}

Answer all 8 questions. Be specific. Use numbers where the paper provides them. 

1. I/O SIGNATURE: What goes in, what comes out? Modalities, shapes, rates.
2. NOVELTY: What is the single new idea? (Max 2 sentences.)
3. COST: Training compute (GPU-hours), inference cost (VRAM, latency), data requirements. Translate these into the project's specific constraints: {constraints}.
4. BASELINES BEATEN: Which baselines, on which metrics, by how much?
5. BASELINES MISSING: What should they have compared against but didn't?
6. ABLATIONS THAT MATTERED: Which components actually contributed to the result?
7. FAILURE MODES: Where does this break? What assumptions does it make?
8. INTEGRATION DIFFICULTY: How hard is this to add to the project's current stack?

Be concise. An engineer will read this in 5 minutes to decide whether to act.
```

### Stage 6: Action Plan Prompt

```
Based on the triage report below, produce an ACTION PLAN.

TRIAGE REPORT:
{triage_report}

PROJECT CONTEXT:
{project_context_card}

Choose a verdict:
- IMPLEMENT: This directly advances the current milestone. Provide a concrete checklist.
- MONITOR: Not actionable now. Define a specific trigger condition for revisiting.
- READ DEEPER: Specify exactly which sections to read and what questions to answer.
- IGNORE: Not relevant. One-line reason.

For IMPLEMENT:
- List specific files/modules to create or modify
- List the loss function(s) to implement (with equation numbers)
- List hyperparameters to start with
- Define the minimal experiment that validates the approach
- Define the success criterion

For MONITOR:
- Write a trigger condition (e.g., "Revisit when starting Milestone 5: streaming inference")
- Write why it's not actionable now

For READ DEEPER:
- Specify exact sections (e.g., "Read §3.2 and §4.1 only")
- Specify what questions to answer while reading
```

---

## 7. Configuration

### `~/.paper-agent/config.yaml`

```yaml
llm:
  provider: anthropic  # or openai, ollama, etc.
  model: claude-sonnet-4-6
  vision_model: claude-sonnet-4-6  # must support images
  temperature: 0.0  # we want deterministic extraction
  max_tokens: 4096

pdf:
  dpi: 300
  fast_mode: false  # skip vision LLM, text-only extraction

storage:
  root: ~/.paper-agent

ui:
  port: 8501
  theme: dark
```

---

## 8. Project Setup

### Package structure

```
paper-agent/
├── pyproject.toml
├── src/
│   ├── __init__.py
│   ├── app.py                    # Streamlit entry point
│   ├── state.py                  # AgentState TypedDict + state helpers
│   ├── graph.py                  # LangGraph graph definitions
│   ├── nodes/                    # One file per graph node
│   │   ├── __init__.py
│   │   ├── extract.py            # PDF → raw text + figures
│   │   ├── screen.py             # Stage 1
│   │   ├── anatomy.py            # Stage 2
│   │   ├── triage.py             # Stage 3
│   │   ├── skeptic.py            # Stage 4
│   │   ├── transform.py          # Math→pseudocode etc.
│   │   ├── verdict.py            # Action plan
│   │   └── persist.py            # Write to filesystem
│   ├── prompts/                  # Version-controlled prompt templates
│   │   ├── __init__.py
│   │   ├── screener.py
│   │   ├── anatomy.py
│   │   ├── triage.py
│   │   ├── skeptic.py
│   │   └── verdict.py
│   ├── storage.py                # Read/write to ~/.paper-agent/
│   ├── context.py                # Load/update Project Context Card
│   └── ui/                       # Streamlit components
│       ├── __init__.py
│       ├── library.py
│       ├── detail.py
│       ├── ingest.py
│       └── query.py
└── templates/                    # Markdown templates for reports
    ├── triage.md.j2
    ├── anatomy.md.j2
    └── action.md.j2
```

### Dependencies (`pyproject.toml`)

```toml
[project]
name = "paper-agent"
version = "0.1.0"
dependencies = [
    "streamlit",
    "langgraph",
    "langchain",
    "langchain-anthropic",  # or langchain-openai
    "pymupdf",              # PDF text extraction
    "pdf2image",            # PDF → images for vision LLM
    "pillow",               # Image handling
    "pyyaml",               # Config + metadata files
    "jinja2",               # Report templates
]
```

---

## 9. Build Order

| Step | What | Output |
|------|------|--------|
| 1 | Directory structure + `config.yaml` + `context.md` for gemma-s2s | Skeleton exists |
| 2 | `storage.py` — read/write helpers for all file types | Can persist/load papers |
| 3 | LangGraph with just Stage 1 (screener) + dummy nodes | End-to-end flow works |
| 4 | PDF extraction node (text only, no figures) | Can parse PDFs |
| 5 | Stages 2–4 + Transform + Verdict nodes | Full pipeline works |
| 6 | Streamlit UI — library view + upload + detail view | Usable UI |
| 7 | Add vision LLM for figure extraction | Handles diagrams |
| 8 | Cross-paper query graph + UI | Comparative analysis |
| 9 | Context auto-update (agent detects when decisions shift) | Adaptive behavior |

Steps 1–6 are the MVP. Steps 7–9 add the advanced capabilities from the design doc.
