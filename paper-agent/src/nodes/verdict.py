import re

from ..state import AgentState, ActionPlan
from ..prompts import verdict as prompts
from .llm import llm_call, format_project_context


def run_verdict(state: AgentState) -> AgentState:
    """Produce the final verdict and action plan."""
    raw = state["raw_paper"]
    triage = state["triage"]
    ctx = format_project_context(state["project_id"])

    triage_text = "\n".join([
        f"1. I/O: {triage.get('io_signature', '')}",
        f"2. Novelty: {triage.get('novelty', '')}",
        f"3. Cost: {triage.get('cost_estimate', '')}",
        f"8. Integration: {triage.get('integration_difficulty', '')}",
    ])

    user = prompts.USER.format(
        goal=ctx["goal"],
        milestone=ctx["milestone"],
        open_decisions=ctx["open_decisions"],
        locked_decisions=ctx["locked_decisions"],
        constraints=ctx["constraints"],
        title=raw["title"],
        triage=triage_text,
        limitations=state.get("limitations", ""),
    )

    response = llm_call(prompts.SYSTEM, user)

    state["verdict"] = _parse_verdict(response)
    state["current_stage"] = "persist"
    return state


def _parse_verdict(response: str) -> ActionPlan:
    lines = response.split("\n")
    verdict = "monitor"
    summary = ""
    confidence = "medium"
    steps = []
    trigger = None
    scoped_reading = None

    in_steps = False
    in_trigger = False
    in_reading = False

    for line in lines:
        lower = line.strip().lower()

        if lower.startswith("verdict:"):
            val = line.split(":", 1)[1].strip().lower()
            for v in ["implement", "monitor", "read_deeper", "ignore"]:
                if v in val:
                    verdict = v
                    break

        elif lower.startswith("confidence:"):
            val = line.split(":", 1)[1].strip().lower()
            if "high" in val:
                confidence = "high"
            elif "low" in val:
                confidence = "low"

        elif lower.startswith("summary:"):
            summary = line.split(":", 1)[1].strip()

        elif "concrete step" in lower or "checklist" in lower or lower.startswith("steps:"):
            in_steps = True
            in_trigger = False
            in_reading = False

        elif "trigger" in lower:
            in_trigger = True
            in_steps = False
            in_reading = False
            trigger = line.split(":", 1)[-1].strip() if ":" in line else ""

        elif "scoped reading" in lower or "section" in lower:
            in_reading = True
            in_steps = False
            in_trigger = False

        elif in_steps and line.strip() and (line.strip()[0].isdigit() or line.strip().startswith("-")):
            steps.append(line.strip().lstrip("-* 0123456789.) "))
        elif in_trigger and line.strip():
            trigger = (trigger + " " + line.strip()).strip() if trigger else line.strip()
        elif in_reading and line.strip():
            if scoped_reading:
                scoped_reading += " " + line.strip()
            else:
                scoped_reading = line.strip()

    return ActionPlan(
        verdict=verdict,
        summary=summary or response[:300],
        concrete_steps=steps,
        trigger_condition=trigger,
        scoped_reading=scoped_reading,
    )
