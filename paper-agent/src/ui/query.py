"""Streamlit component: Cross-paper comparative query."""

import streamlit as st
from .. import storage
from ..nodes.llm import llm_call


def render_query(project_id: str) -> None:
    """Render the cross-paper query interface."""

    st.markdown("## 🔍 Cross-Paper Query")
    st.caption("Ask a comparative question across all papers in your library.")

    papers = storage.list_papers(project_id)

    if len(papers) < 2:
        st.info("Ingest at least 2 papers to enable cross-paper queries.")
        return

    # Paper selector
    paper_ids = [p["paper_id"] for p in papers]
    selected = st.multiselect(
        "Papers to query (default: all)",
        options=paper_ids,
        default=[],
        format_func=lambda x: f"{x} ({_verdict_short(paper_ids, papers, x)})",
    )

    if not selected:
        selected = paper_ids

    query = st.text_area(
        "Question",
        placeholder="E.g., 'How does the latency compare across these papers? Which codec would work best for my constraints?'",
    )

    if st.button("Query", type="primary") and query:
        _run_query(project_id, selected, query)


def _verdict_short(paper_ids: list[str], papers: list[dict], pid: str) -> str:
    for p in papers:
        if p["paper_id"] == pid:
            v = p.get("verdict", "unknown")
            return {"implement": "IMP", "monitor": "MON", "read_deeper": "READ", "ignore": "IGN"}.get(v, "?")
    return "?"


def _run_query(project_id: str, paper_ids: list[str], query: str) -> None:
    """Load paper triage reports + metadata, then run a comparative LLM query."""

    with st.spinner("Loading papers and analyzing..."):
        # Gather all triage reports and metadata
        contexts = []
        for pid in paper_ids:
            data = storage.read_paper(project_id, pid)
            meta = data.get("metadata_yaml", "")
            triage = data.get("triage_md", "")
            contexts.append(f"--- PAPER: {pid} ---\nMETADATA:\n{meta}\n\nTRIAGE:\n{triage[:3000]}")

        combined = "\n\n".join(contexts)

        system = """\
You are comparing research papers for an ML engineer. Given the paper summaries below, answer the user's comparative question.
Be specific. Use numbers if the papers provide them. If a paper doesn't provide relevant information, say so.
Structure your answer clearly. Use a table if comparing multiple metrics across papers.
"""

        user = f"""\
PAPERS IN LIBRARY:
{combined}

USER QUESTION:
{query}
"""

        response = llm_call(system, user)
        st.markdown(response)
