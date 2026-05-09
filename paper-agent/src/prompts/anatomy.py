SYSTEM = """\
You are analyzing the STRUCTURE of an ML paper — not evaluating its quality, not summarizing it.
Extract only the architectural skeleton: components, connections, shapes, losses, tables, ablations.
"""

USER = """\
PAPER: {title}
FULL TEXT:
{full_text}

Extract the following. Be specific. Use exact numbers and names from the paper.

1. ARCHITECTURE
Describe the system as a text block diagram. For each component:
- Name and purpose (one line)
- Input and output tensor shapes (if specified)
- How it connects to other components
If there is a backbone model and new modules added to it, clearly distinguish them.

2. LOSS FUNCTIONS
List every loss function. For each:
- Equation number
- What it optimizes
- Any hyperparameters (λ, β, α, temperature) and their values

3. KEY TABLES
For each results table in the paper:
- Table number and what it shows
- Metrics reported
- Baselines compared
- Rough magnitude of improvement
- Whether error bars or statistical tests are reported

4. ABLATIONS
List every ablation study:
- What was varied
- What was measured
- Which variation had the largest effect
- Which components were found to be unnecessary (decorative)
"""
