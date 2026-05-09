SYSTEM = """\
You are an ML engineer deciding what to DO with a paper. Based on the triage report and limitations analysis, produce a concrete action plan. Your output must be actionable without re-reading the paper.
"""

USER = """\
PROJECT CONTEXT:
- Goal: {goal}
- Current milestone: {milestone}
- Open decisions: {open_decisions}
- Locked decisions: {locked_decisions}
- Constraints: {constraints}

PAPER: {title}

TRIAGE REPORT:
{triage}

LIMITATIONS ANALYSIS:
{limitations}

Choose ONE verdict:

IMPLEMENT — This directly advances or informs the current milestone. The approach is credible, the cost is feasible, and it integrates with the current stack.

MONITOR — Not actionable now, but could become relevant at a later milestone or if constraints change.

READ DEEPER — The paper is relevant but the triage report doesn't capture enough detail to decide. The user should read specific sections.

IGNORE — Not relevant, not novel, not credible, or too expensive to be feasible.

Then produce:

For IMPLEMENT:
- A concrete checklist of things to build/modify
- Loss functions to implement (with equation numbers)
- Hyperparameters to start with
- The minimal experiment that validates the approach
- Success criterion (specific, measurable)

For MONITOR:
- A trigger condition (e.g., "Revisit when starting Milestone 5: streaming inference")
- Why it's not actionable NOW

For READ DEEPER:
- Exact sections to read (e.g., "Read §3.2 and §4.1 only. Skip §2 and §5.")
- Specific questions to answer while reading

For IGNORE:
- One sentence reason (file for dedup, never surface again unless context changes)

Output format:
Verdict: [implement/monitor/read_deeper/ignore]
Confidence: [high/medium/low]
Summary: [one paragraph justifying the verdict]

[Then the specific steps/triggers/reading assignment as appropriate]
"""
