from ..state import AgentState, TriageReport
from ..prompts import triage as prompts
from .llm import llm_call, format_project_context


def run_triage(state: AgentState) -> AgentState:
    """Stage 3: Produce the 8-question Triage Report."""
    raw = state["raw_paper"]
    anatomy = state["anatomy"]
    ctx = format_project_context(state["project_id"])

    # Format anatomy as a readable block
    anatomy_text = f"""Architecture Blocks: {anatomy.get("architecture_blocks", [])}
Loss Functions: {anatomy.get("loss_functions", [])}
Key Tables: {anatomy.get("key_tables", [])}"""

    user = prompts.USER.format(
        goal=ctx["goal"],
        milestone=ctx["milestone"],
        constraints=ctx["constraints"],
        locked_decisions=ctx["locked_decisions"],
        title=raw["title"],
        authors=", ".join(raw["authors"]) if raw["authors"] else "Unknown",
        anatomy=anatomy_text,
        full_text=raw["full_text"][:20000],
    )

    response = llm_call(prompts.SYSTEM, user)

    state["triage"] = _parse_triage(response)
    state["current_stage"] = "skeptic"
    return state


def _parse_triage(response: str) -> TriageReport:
    fields = {
        "io_signature": "",
        "novelty": "",
        "cost_estimate": "",
        "baselines_beaten": "",
        "baselines_missing": "",
        "ablations_that_mattered": "",
        "failures_and_assumptions": "",
        "integration_difficulty": "",
    }

    current_key = None
    for line in response.split("\n"):
        line_stripped = line.strip()
        lower = line_stripped.lower()

        # Match section headers like "1. I/O SIGNATURE" or "## 1. I/O Signature"
        if "i/o" in lower or "signature" in lower or lower.startswith("1."):
            current_key = "io_signature"
        elif "novelty" in lower or lower.startswith("2."):
            current_key = "novelty"
        elif "cost" in lower or lower.startswith("3."):
            current_key = "cost_estimate"
        elif "baselines beaten" in lower or lower.startswith("4."):
            current_key = "baselines_beaten"
        elif "baselines missing" in lower or lower.startswith("5."):
            current_key = "baselines_missing"
        elif "ablation" in lower or lower.startswith("6."):
            current_key = "ablations_that_mattered"
        elif "failure" in lower or "assumption" in lower or lower.startswith("7."):
            current_key = "failures_and_assumptions"
        elif "integration" in lower or lower.startswith("8."):
            current_key = "integration_difficulty"
        elif current_key:
            fields[current_key] += line + "\n"

    return TriageReport(
        io_signature=fields["io_signature"].strip(),
        novelty=fields["novelty"].strip(),
        cost_estimate=fields["cost_estimate"].strip(),
        baselines_beaten=fields["baselines_beaten"].strip(),
        baselines_missing=fields["baselines_missing"].strip(),
        ablations_that_mattered=fields["ablations_that_mattered"].strip(),
        failures_and_assumptions=fields["failures_and_assumptions"].strip(),
        integration_difficulty=fields["integration_difficulty"].strip(),
    )
