SYSTEM = """\
You are producing an ENGINEERING TRIAGE REPORT for a specific project.
This is the most important document an engineer will read about this paper.
Be precise. Use numbers. Answer every question. If the paper doesn't provide information for a question, say so explicitly.
"""

USER = """\
PROJECT CONTEXT:
- Goal: {goal}
- Current milestone: {milestone}
- Constraints: {constraints}
- Locked decisions: {locked_decisions}

PAPER TITLE: {title}
PAPER AUTHORS: {authors}

ANATOMY (from structural extraction):
{anatomy}

FULL PAPER TEXT (for reference):
{full_text}

Answer all 8 questions. Each answer should be 1-3 paragraphs, specific and actionable.

1. I/O SIGNATURE
What goes in and what comes out? Modalities (audio, text, image), exact shapes/sample rates/frame rates, tokenization method. Intermediate representations if relevant.

2. NOVELTY
What is the ONE new idea in this paper? Two sentences maximum. What existing component does it replace or augment?

3. COST ESTIMATE
Training: GPU-hours, number of GPUs, wall-clock time, dataset size.
Inference: VRAM needed, latency (ms), throughput (tokens/sec or RTF).
Data: quantity, quality, preprocessing complexity.
Then TRANSLATE these into the project's specific constraints: {constraints}.
E.g., "This would take X hours on your A100" or "This won't fit on your GPU budget."

4. BASELINES BEATEN
Which baselines? On which metrics? By what margin? Are these the right baselines for this problem?

5. BASELINES MISSING
What should the authors have compared against but didn't? Are there known stronger baselines they omitted?

6. ABLATIONS THAT MATTERED
Which components actually contributed to the final result? Which were decorative (present but don't help)? Rank by importance.

7. FAILURE MODES & ASSUMPTIONS
Where does this method break? What assumptions does it make (clean speech, single speaker, English only, offline processing, etc.)? What did the authors NOT test?

8. INTEGRATION DIFFICULTY
How hard would it be to add this to the project's current stack? Does it conflict with any locked decisions? What would need to change?
"""
