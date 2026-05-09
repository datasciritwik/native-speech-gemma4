SYSTEM = """\
You transform academic paper content into engineering artifacts: pseudocode, feasibility estimates, and implementation roadmaps.
DO NOT summarize. Translate format.
"""

PSEUDOCODE = """\
Convert the following equations/loss functions into executable pseudocode (Python-like).

PAPER: {title}
EQUATIONS/LOSS FUNCTIONS:
{loss_functions}

For each equation:
- Use descriptive variable names (not Greek letters)
- Include tensor shapes as comments
- Note any ambiguities the paper doesn't resolve
- Flag where the paper is unclear about dimensions or normalization
"""

FEASIBILITY = """\
Translate the resource requirements of this paper into the user's specific context.

PAPER: {title}
REPORTED RESOURCES: {reported_resources}

USER CONSTRAINTS: {constraints}

Provide:
1. What this would cost on the user's hardware (time + money)
2. Whether any step is fundamentally impossible on their setup
3. What could be scaled down (smaller batches, LoRA only, fewer iterations)
4. A realistic estimate of what it would take to reproduce the key result (not the whole paper)
"""

ROADMAP = """\
Extract the dependency chain from this paper's related work and methodology sections.

PAPER: {title}
FULL TEXT (sections: introduction, related work, methodology):
{text}

Produce an ordered reading/implementation list:
1. What prior papers/techniques must be understood first
2. What components can be used off-the-shelf vs. must be built from scratch
3. The minimal sequence of steps to implement this paper's core idea
"""
