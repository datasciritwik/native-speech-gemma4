# Engineering Paper Agent — Capability & Philosophy Design

> A specialized agent that triages, extracts, and transforms academic papers into **engineering intelligence**. It does not summarize; it answers "what do I build, what does it cost, and is it better than what I have?"

---

## 0. Core Philosophy

The agent's north star: **an engineer reads a paper to decide whether to act, not to understand.** Every feature either moves the engineer closer to a go/no-go decision or closer to a correct implementation. Features that do neither are waste.

This implies three design principles:

1. **Default to rejection.** Most papers are irrelevant to a given project. The agent should be optimized to dismiss papers quickly, not to ingest them deeply. A false positive (deep-reading an irrelevant paper) costs hours; a false negative (missing a key paper) gets caught by the community.
2. **The unit of output is a decision, not a summary.** Every report should end with a concrete recommendation: implement, monitor, ignore, or read-deeper.
3. **The agent serves the project, not the reader.** It must maintain persistent context about what the user is building, their constraints (GPU budget, latency targets, dataset size), and what they've already read.

---

## 1. The Triage Philosophy (Reading Like an Engineer)

An experienced engineer doesn't read papers linearly. They execute a rapid 4-stage funnel that eliminates 90%+ of papers in under 5 minutes and reserve deep reading for the 1–2 papers per week that directly impact their work. The agent must emulate this funnel.

### Stage 1 — The Screener (Target: <60 seconds, eliminate 80%)

**Goal:** Determine if this paper is relevant *enough* to spend 5 more minutes on.

The screener must answer three binary questions:

| Question | What it means |
|----------|---------------|
| **Does this touch my problem domain?** | Not "is it about ML" — is it about *my specific subproblem* (e.g., neural audio codecs, adapter-based speech generation, streaming inference). |
| **Is this a capability I don't already have?** | If the paper achieves X and your system already does X at comparable quality, it's irrelevant unless it does X cheaper. |
| **Is the claimed improvement large enough to matter?** | A 0.3 BLEU improvement on a benchmark you don't use is noise. A 2× latency reduction on a metric you care about is signal. |

**Context-dependence is the hard part.** "Relevance" is a function of the user's current project state. A paper about low-frame-rate codecs is high-priority during Milestone 2 (codec selection) but low-priority during Milestone 6 (full-duplex debugging). The agent must know what milestone the user is on and what decisions are still open vs. settled.

**Conceptual mechanism:** The screener compares the paper's abstract + introduction against a user-maintained "project context card" containing:
- Current milestone and its success criteria
- Decisions already locked in (e.g., "we chose Mimi, not EnCodec")
- Decisions still open (e.g., "haven't chosen between single-stream and multi-stream")
- Known pain points (e.g., "TTFAF is 800 ms, target is 300 ms")

A paper scores high urgency if it addresses an *open decision* or a *known pain point*. It scores low urgency if it addresses a locked decision or an irrelevant subproblem.

**Irrelevance vs. foundational shift.** The danger is dismissing a paper that makes your entire approach obsolete. A "foundational shift" paper typically:
- Claims a capability previously thought impossible (e.g., "200 ms full-duplex on a single consumer GPU")
- Changes the cost structure by an order of magnitude (e.g., "trains in 1/10th the compute")
- Introduces a new problem formulation that makes your current one a special case

The agent should flag papers that match these patterns even if they fail the screener, with a special label: **"Potential paradigm shift — verify before ignoring."**

### Stage 2 — Structural Anatomy (Target: <5 minutes)

**Goal:** Extract the paper's architectural skeleton without reading prose.

Engineers don't read papers; they read diagrams, tables, and equations. The agent must isolate these structural elements:

**Visual-first extraction:**
- **Architecture diagram (Figure 1 or 2 in most papers):** What blocks exist? What connects to what? What are the tensor shapes at each boundary? This is the single highest-signal element in most ML papers.
- **Loss function (usually an equation):** What is being optimized? Multi-task or single-task? Any auxiliary losses? This tells you what the authors actually cared about.
- **Results tables (Tables 1–3):** What baselines are compared? What metrics? What's the gap? Look for: (a) missing baselines that should be there, (b) metrics that are proxies for what you actually care about, (c) error bars or lack thereof.
- **Ablation table:** What design choices actually mattered vs. what was decoration? This is often the most honest part of the paper.

**What to skip in Stage 2:**
- Related Work section (the agent reads this separately — see §4, Comparative Analysis)
- Introduction beyond the first and last paragraphs
- Any prose that doesn't directly describe a diagram, equation, or table

**Output of Stage 2:** A one-page "anatomy sheet" showing the architecture as a block diagram, the loss function, the key results, and what ablations mattered. The engineer should be able to sketch the architecture from this sheet alone.

### Stage 3 — Targeted Extraction (The Triage Report)

**Goal:** Produce a structured report that answers the 8 questions every engineer needs answered before they can act on a paper.

This is the core output of the system. The schema:

#### The 8-Question Triage Report Schema

**1. What goes in and what comes out?**
- Input modality, shape, sample rate, tokenization
- Output modality, shape, frame rate, decoding
- Any intermediate representations
- *Why this matters:* Until you know the I/O signature, you cannot reason about integration.

**2. What is the novel component?** (One sentence, maximum two.)
- Is it a new architecture? A new loss? A new data pipeline? A new inference strategy?
- What existing component does it replace or augment?
- *Why this matters:* If the novelty is orthogonal to your problem, you can stop here.

**3. What does it cost?**
- Training compute (GPU-hours, wall-clock time, dataset size)
- Inference compute (VRAM, latency, throughput, batch size)
- Data requirements (labeled/unlabeled, quantity, quality, preprocessing complexity)
- *Why this matters:* A SOTA result on 512 H100s for 3 months is a non-starter for most teams. The agent must translate raw numbers into the user's constraint language (e.g., "This would take 4 months on your 2×A100 setup — not viable without renting.")

**4. What baselines does it beat, and by how much?**
- Which baselines? Are they the right ones?
- Which metrics? Are they the ones you care about?
- Statistical significance? Error bars?
- *Why this matters:* A paper that beats weak baselines on irrelevant metrics is noise.

**5. What baselines are missing?**
- What should the authors have compared against but didn't?
- Are there known methods that would be stronger competitors?
- *Why this matters:* Missing baselines are the #1 sign of a paper that's less impressive than it looks.

**6. What ablations mattered?**
- Which components contributed how much to the final result?
- Which components were decorative (present in the architecture but not ablating meaningfully)?
- *Why this matters:* Tells you what you actually need to implement vs. what you can simplify.

**7. What is the failure mode?**
- Where does the method break? (OOD data, noisy inputs, long sequences, rare tokens)
- What assumptions does it make? (clean speech, single speaker, English-only, offline processing)
- What did the authors not test?
- *Why this matters:* The paper tells you where it works. The agent must find where it doesn't.

**8. Integration difficulty for [user's project]?**
- Can this be bolted on as an adapter, or does it require retraining the backbone?
- Does it conflict with any locked-in design decisions?
- Does it depend on components/libraries the user isn't using?
- *Why this matters:* A brilliant idea that requires rewriting the codec interface from scratch is a different decision than one that's a drop-in LoRA module.

### Stage 4 — Evaluation & Limitations (The Skeptic's Pass)

**Goal:** Actively search for reasons the paper's results won't generalize to the user's setting.

This is a separate pass because it requires a different stance: the agent must assume the paper is *wrong* or *overclaimed* and look for evidence.

**Patterns the agent should flag:**

- **Compute-matched comparisons.** Did the authors give their method 10× more compute than baselines? Check if the comparison is fair-parameter or fair-FLOP.
- **Benchmark contamination.** Is the test set likely in the training data? (Common in web-scraped datasets.)
- **Cherry-picked samples.** Are the qualitative examples suspiciously clean? Are there any failure cases shown?
- **Hidden assumptions in the problem setup.** Does the method assume access to ground-truth alignments? Oracle segmentations? Clean speech with no background noise?
- **Hyperparameter fragility.** Do the ablations suggest the method only works in a narrow regime? (Common sign: small changes in learning rate or loss weight cause large drops.)
- **The "one GPU" trick.** Authors train on 64 GPUs but report inference cost on 1 GPU. The agent should catch this.

**Output of Stage 4:** A "Limitations Addendum" to the Triage Report listing (a) limitations the authors acknowledge, (b) limitations the authors don't acknowledge but should, and (c) specific risks for the user's project context.

---

## 2. Transformation vs. Summarization

Summarization is lossy compression: paper → shorter text. Transformation is format translation: paper → engineering artifact. The agent must do the latter.

### Transformation 1: Math → Pseudocode

Academic papers express algorithms in notation optimized for compactness and generality. Engineers need them expressed as executable logic.

**What this transformation requires:**
- Recognizing when an equation defines a forward pass, a loss computation, a sampling procedure, or an update rule
- Translating Greek letters and subscripts into named variables with explicit shapes
- Handling the "index gymnastics" that papers use (summations over unspecified sets, broadcasting assumed but not stated)
- Flagging ambiguity explicitly: "The paper doesn't specify whether this normalization is over the feature dimension or the batch dimension. In similar architectures it's usually feature-dim. Test both."

**Example (conceptual):**

> **Paper equation:** `L = Σ_t ||x_t - D(E(x_t))||² + β·Σ_k ||z_k - sg[e_k]||²`
>
> **Transformed pseudocode:**
> ```
> def compute_loss(x: Tensor[B, T, D]) -> Tensor[scalar]:
>     # x: batch of audio frames, B=batch, T=timesteps, D=features
>     z = encoder(x)                     # z: [B, T//S, C] — downsampled by stride S
>     quantized, indices = rvq(z)        # quantized: [B, T//S, C], indices: [B, T//S, K]
>     reconstructed = decoder(quantized) # [B, T, D]
>     
>     recon_loss = mse(x, reconstructed)
>     commit_loss = beta * mse(z, quantized.detach())  # note: stop-gradient on quantized
>     
>     return recon_loss + commit_loss
> ```

### Transformation 2: Resource Requirements → Feasibility Statement

Papers report resource usage in their context. The agent must translate it into the user's context.

**What this transformation requires:**
- A user-maintained "resource profile" (available GPUs, budget, time constraints, storage)
- Unit normalization: convert all paper-reported numbers to a common unit (GPU-hours at bf16), then scale to the user's hardware
- Flagging when the paper doesn't report enough information to estimate (e.g., "the paper says 'trained on 8 GPUs' but doesn't specify which GPUs or for how long — resource estimate is unreliable")

**Example:**

> **Paper reports:** "Trained on 64 H100-80GB for 2 weeks."
> **Agent computes:** ~21,500 H100-hours.
> **User profile:** 4× A100-40GB, $2,000 budget.
> **Transformation:** "This training run would take ~5,400 A100-hours (accounting for A100 vs H100 throughput gap). At spot pricing (~$1.50/A100-hr), that's ~$8,100 — over your budget. However, a LoRA-only variant (which the paper doesn't do) would likely cost 5–10% of that. Recommendation: worth investigating a LoRA adaptation, not worth attempting full reproduction."

### Transformation 3: Related Work → Implementation Roadmap

The Related Work section is a dependency graph in prose form. The agent should extract it into an ordered list of "what to understand before implementing this paper."

**What this transformation requires:**
- Parsing citations to identify which prior works are foundational (cited by many in the chain) vs. incidental
- Detecting when a paper says "we follow X but change Y" — this is the highest-signal sentence in Related Work
- Generating a reading order: "To implement this paper, first understand Paper A (provides the codec), then Paper B (provides the backbone architecture), then read only §3 of this paper (the novel contribution)"

---

## 3. Actionability & The "Next Steps" Feature

The highest-value output of the system is not the report — it's the **action plan** that follows it. After reading the triage report, the engineer should know exactly what to do next.

### The Action Plan Schema

For every paper, the agent produces one of four top-level verdicts:

| Verdict | Meaning | Action |
|---------|---------|--------|
| **Implement now** | This directly advances the current milestone. | Produce a concrete implementation checklist. |
| **Monitor** | Not actionable now, but could become relevant in a later milestone. | Save to project library with a trigger condition (e.g., "revisit when starting Milestone 5"). |
| **Read deeper** | The paper is relevant but the triage report doesn't capture enough detail to decide. | Specify exactly which sections to read and what questions to answer while reading. |
| **Ignore** | Not relevant, not novel, or not credible. | File with a one-line reason. Never surface again unless the user's context changes materially. |

### For "Implement Now" papers:

The action plan must be concrete enough to act on without re-reading the paper:

- **Exact files/lines to modify** in the user's codebase (if the agent has access to it and the paper maps cleanly)
- **The specific loss function to add** (equation number + pseudocode)
- **The specific hyperparameters to start with** (extracted from the paper's appendix or inferred from ablations)
- **What to test first** (the minimal viable experiment that validates the approach works in the user's setting)
- **What the success criterion is** (e.g., "TTFAF drops below 300 ms on the validation set")

### For "Monitor" papers:

The agent must define a **trigger condition** — a specific, testable predicate that, when true, means this paper is now relevant:

- "Revisit when you start codec selection (Milestone 2)"
- "Revisit if your TTFAF is above 500 ms after implementing the streaming decoder"
- "Revisit if you decide to support Chinese in addition to English"

### For "Read Deeper" papers:

The agent should specify a **scoped reading assignment**, not "read the whole paper":
- "Read §3.2 (the Depth Transformer) and §4.1 (the ablation on number of codebooks). Skip §2 (background) and §5 (related work)."
- "Target question: would splitting your current single transformer into Depth + Temporal reduce your latency below 300 ms?"

### Actionability Anti-patterns the Agent Must Avoid

- **Vague advice:** "Consider using this approach." → Instead: "Replace the `SpeechHead` module in `model.py:142` with this paper's architecture (see pseudocode above)."
- **Unscoped reading assignments:** "Read this paper." → Instead: "Read §3 only."
- **Ignoring the user's constraints:** "This 70B model achieves SOTA." → "This 70B model achieves SOTA but requires 140 GB VRAM for inference. Your hardware budget is 24 GB. Not actionable unless you plan to use an API."

---

## 4. Advanced Concepts & Future Scope

These are capabilities that go beyond single-paper triage and start to build a persistent engineering knowledge system.

### 4.1 Comparative Analysis (Cross-Paper Intelligence)

Once the user has ingested 5–10 papers, the agent should be able to answer *comparative* questions that no single paper addresses.

**Required capabilities:**
- **Maintain a structured paper library** where each ingested paper is stored as its Triage Report (not the raw PDF), indexed by: problem domain, method family, metrics reported, baselines used.
- **Detect contradictions across papers:** "Paper A claims method X outperforms Y. Paper B claims Y outperforms X. Difference: Paper A used a different codec. The comparison is not apples-to-apples."
- **Detect convergent results:** "Three papers independently find that inner monologue improves WER by 15–20%. This is likely a robust finding worth adopting."
- **Track metric drift:** "Papers in 2024 reported TTFAF of 500–800 ms. Papers in 2025 are reporting 200–300 ms. The field is moving fast; your 500 ms baseline from 6 months ago is now behind."

**User-facing output:**
> "This paper's approach (streaming adapter, 300 ms TTFAF) is 40% faster than Paper A from last month (500 ms) but uses 2× the VRAM. The speed comes from a lower frame-rate codec (12.5 Hz vs 50 Hz). Your current codec is 50 Hz — this paper's approach would require a codec migration to adopt. Verdict: Monitor. Trigger: revisit if you switch to Mimi."

### 4.2 Project Alignment Checking (Code-Aware Analysis)

If the agent has access to the user's repository, it can do much sharper triage.

**Required capabilities:**
- **Interface matching:** Read the user's model definition files. Identify the exact I/O signatures. Check if the paper's proposed module can physically connect to the user's architecture without adapter layers.
  - Example: "This paper assumes encoder output at 50 Hz. Your Gemma audio encoder outputs at 25 Hz (40 ms frames). You would need an upsampling layer or to switch to a 20 ms frame encoder."
- **Dependency conflict detection:** "This paper's method depends on Flash-Attention 3. Your codebase uses Flash-Attention 2. Migration cost is non-trivial."
- **Codebase invasiveness estimation:** Classify papers by how deep they cut:
  - **Surface:** Add a new `nn.Module`, plug it into an existing forward pass. (Low risk.)
  - **Medium:** Modify the training loop or loss computation. (Moderate risk.)
  - **Deep:** Change the tokenizer, data pipeline, or backbone architecture. (High risk — requires significant validation.)
- **Stale decision detection:** "You locked in EnCodec during Milestone 2, but three papers since then show Mimi outperforming EnCodec on your target metric. The locked decision may be worth revisiting."

### 4.3 Contextual Awareness (Persistent User Model)

The agent is only as good as its understanding of what the user cares about. This requires a persistent, evolving model of the user's project.

**The Project Context Card (maintained by the agent, editable by the user):**

```
# Active Project
- Goal: Extend Gemma 4 E2B for speech-to-speech output
- Current milestone: Literature survey (Week 1 of ~12)
- Target architecture style: Adapter on frozen backbone (Mini-Omni pattern)

# Open Decisions
- Codec: Mimi vs EnCodec (not yet decided)
- Stream type: Starting single-stream, may evolve to multi-stream
- Inner monologue: Planning to adopt (Moshi-style)

# Locked Decisions
- Backbone: Gemma 4 E2B (frozen)
- Training method: LoRA + speech head (not full fine-tune)
- Framework: PyTorch + HuggingFace transformers

# Constraints
- GPU budget: TBD (likely single A100 or 2× consumer GPUs for early milestones)
- Latency target: <500 ms TTFAF for Milestone 3
- Languages: English first, multilingual later

# Papers Already Ingested
- [List of paper titles + verdicts + trigger conditions]

# Known Pain Points
- None yet (project hasn't started coding)
```

This card is **the lenses through which every paper is read.** Without it, the agent is doing generic summarization. With it, every paper is evaluated against a concrete set of questions the user actually has.

**Maintenance burden on the user:** The user should update this card at each milestone transition (every ~2 weeks). The agent should prompt for updates when it detects the user's questions have shifted (e.g., "You're now asking about streaming inference optimization. Should I update your current milestone to Milestone 5?").

### 4.4 Longitudinal Memory (What the User Has Already Learned)

Beyond the paper library, the agent should track what the user has *internalized* vs. what they still need to learn.

**Required capabilities:**
- When the user reads a paper, mark its key concepts as "exposed." The agent shouldn't re-explain RVQ in paper #5 if the user deep-read EnCodec in paper #2.
- When the user's questions reveal a gap, flag it: "You're asking about the Depth Transformer, but that concept was introduced in Moshi §3.2. You skimmed Moshi but didn't deep-read it. Want me to produce a targeted extraction of just §3.2?"
- **Adaptive depth:** Early in the project (literature survey phase), the agent should be more permissive — surface papers that are adjacent but not directly actionable, because the user is building their mental map. Later (implementation phase), the agent should be aggressively utilitarian — only surface papers that directly affect the current milestone.

---

## 5. Summary: The Agent's Capability Requirements

Distilled to a capability checklist, the agent must be able to:

| # | Capability | Priority |
|---|-----------|----------|
| 1 | Accept and maintain a persistent Project Context Card | P0 (useless without it) |
| 2 | Execute 4-stage triage (Screen → Anatomy → Extract → Skeptic) | P0 |
| 3 | Produce an 8-question Triage Report for any paper | P0 |
| 4 | Transform math → pseudocode, resources → feasibility, related work → roadmap | P0 |
| 5 | Produce a verdict + concrete action plan (Implement/Monitor/Read/Ignore) | P0 |
| 6 | Maintain a searchable paper library indexed by the Triage Report schema | P1 |
| 7 | Perform cross-paper comparative analysis | P1 |
| 8 | Read user's codebase and check interface/dependency compatibility | P1 |
| 9 | Track user's knowledge state (exposed vs. unexposed concepts) | P2 |
| 10 | Detect stale decisions and prompt for re-evaluation | P2 |
| 11 | Adapt filtering strictness to project phase (survey vs. implementation) | P2 |

---

## 6. What This Agent Is NOT

Being explicit about boundaries prevents scope creep:

- **Not a paper search engine.** The user finds papers (arXiv, Semantic Scholar, Twitter, colleagues). The agent processes them. Paper *discovery* is a separate problem.
- **Not a conversation partner about theory.** The agent answers "how do I build this" not "why does this work." Theoretical depth is available on demand but not the default.
- **Not a replacement for reading code.** The agent extracts from the paper. The user still needs to read the open-source implementation. The agent can point to specific files/lines but should not claim to understand code it hasn't executed.
- **Not a one-shot tool.** The agent's value compounds with each paper ingested, because cross-paper patterns emerge. A single-paper triage tool is marginally useful. A library of 20+ triaged papers with comparative analysis is transformative.
