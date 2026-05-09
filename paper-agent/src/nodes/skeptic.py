from ..state import AgentState
from ..prompts import skeptic as prompts
from .llm import llm_call


def run_skeptic(state: AgentState) -> AgentState:
    """Stage 4: Skeptic's pass — find limitations and failure modes."""
    raw = state["raw_paper"]
    triage = state["triage"]

    triage_text = f"""I/O: {triage.get("io_signature", "")}
Novelty: {triage.get("novelty", "")}
Cost: {triage.get("cost_estimate", "")}
Baselines Beaten: {triage.get("baselines_beaten", "")}
"""

    user = prompts.USER.format(
        title=raw["title"],
        full_text=raw["full_text"][:15000],
        triage=triage_text,
    )

    response = llm_call(prompts.SYSTEM, user)
    state["limitations"] = response.strip()
    state["current_stage"] = "transform"
    return state
