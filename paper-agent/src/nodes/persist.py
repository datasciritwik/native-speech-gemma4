from ..state import AgentState
from .. import storage


def run_persist(state: AgentState) -> AgentState:
    """Write all extracted data to ~/.paper-agent/."""
    pid = state["project_id"]
    paper_id = state["paper_id"]
    raw = state["raw_paper"]

    # Metadata
    storage.write_metadata(
        project_id=pid,
        paper_id=paper_id,
        title=raw["title"],
        authors=raw["authors"],
        url=raw.get("url"),
        year=raw.get("year"),
    )

    # Stage outputs
    if "screener" in state:
        storage.write_screener(pid, paper_id, state["screener"])

    if "anatomy" in state:
        storage.write_anatomy(pid, paper_id, state["anatomy"])

    if "triage" in state:
        storage.write_triage(pid, paper_id, state["triage"])

    if "limitations" in state and state["limitations"]:
        storage.write_limitations(pid, paper_id, state["limitations"])

    if "transformations" in state and state["transformations"]:
        storage.write_transformations(pid, paper_id, state["transformations"])

    # Verdict + action
    if "verdict" in state:
        v = state["verdict"]
        storage.write_action(pid, paper_id, v)
        storage.update_metadata_verdict(
            pid, paper_id,
            verdict=v.get("verdict", "monitor"),
            confidence=v.get("verdict_confidence", "medium"),
            trigger=v.get("trigger_condition"),
        )

    state["current_stage"] = "done"
    return state
