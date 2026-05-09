from ..state import AgentState
from ..prompts import transform as prompts
from .llm import llm_call, format_project_context


def run_transform(state: AgentState) -> AgentState:
    """Transform paper content into engineering artifacts (pseudocode, feasibility, roadmap)."""
    raw = state["raw_paper"]
    anatomy = state["anatomy"]
    ctx = format_project_context(state["project_id"])

    loss_fns = "\n".join(anatomy.get("loss_functions", []))
    triage = state["triage"]

    transformations = {}

    # 1. Math → Pseudocode
    if loss_fns.strip():
        user_pseudo = prompts.PSEUDOCODE.format(
            title=raw["title"],
            loss_functions=loss_fns,
        )
        transformations["pseudocode"] = llm_call(prompts.SYSTEM, user_pseudo)

    # 2. Resource → Feasibility
    user_feasibility = prompts.FEASIBILITY.format(
        title=raw["title"],
        reported_resources=triage.get("cost_estimate", "Not specified in paper"),
        constraints=ctx["constraints"],
    )
    transformations["feasibility"] = llm_call(prompts.SYSTEM, user_feasibility)

    # 3. Related Work → Roadmap
    user_roadmap = prompts.ROADMAP.format(
        title=raw["title"],
        text=raw["full_text"][:12000],
    )
    transformations["roadmap"] = llm_call(prompts.SYSTEM, user_roadmap)

    state["transformations"] = transformations
    state["current_stage"] = "verdict"
    return state
