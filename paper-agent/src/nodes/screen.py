from ..state import AgentState, ScreenerResult
from ..prompts import screener as prompts
from .llm import llm_call, format_project_context


def run_screener(state: AgentState) -> AgentState:
    """Stage 1: Screen the paper for relevance."""
    raw = state["raw_paper"]
    ctx = format_project_context(state["project_id"])

    user = prompts.USER.format(
        goal=ctx["goal"],
        milestone=ctx["milestone"],
        open_decisions=ctx["open_decisions"],
        locked_decisions=ctx["locked_decisions"],
        constraints=ctx["constraints"],
        title=raw["title"],
        authors=", ".join(raw["authors"]) if raw["authors"] else "Unknown",
        abstract=raw["abstract"] or raw["full_text"][:2000],
    )

    response = llm_call(prompts.SYSTEM, user)

    result = _parse_screener(response)
    state["screener"] = result
    state["current_stage"] = "anatomy"
    return state


def _parse_screener(response: str) -> ScreenerResult:
    relevance = "irrelevant"
    urgency = "low"
    reason = ""

    for line in response.split("\n"):
        line = line.strip()
        if line.lower().startswith("relevance:"):
            val = line.split(":", 1)[1].strip().lower()
            if "paradigm" in val:
                relevance = "paradigm_shift"
            elif "relevant" in val:
                relevance = "relevant"
        elif line.lower().startswith("urgency:"):
            val = line.split(":", 1)[1].strip().lower()
            if "high" in val:
                urgency = "high"
            elif "medium" in val:
                urgency = "medium"
        elif line.lower().startswith("reason:"):
            reason = line.split(":", 1)[1].strip()

    return ScreenerResult(relevance=relevance, urgency=urgency, reason=reason)
