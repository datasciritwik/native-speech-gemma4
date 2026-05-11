"""Streamlit component: Cross-paper comparative query."""

import streamlit as st
from .. import storage
from .. import context as ctx
from ..nodes.llm import llm_call

GENERIC_PROMPTS = {
    "Custom question...": "",
    "Compare methodologies": (
        "Compare the methodologies across these papers. "
        "What are the key differences and similarities in their approaches? "
        "Which design choices are most consequential?"
    ),
    "Main contributions": (
        "What are the main contributions of each paper? "
        "Which paper seems most impactful and why? "
        "How novel is each contribution relative to the others?"
    ),
    "Experimental results": (
        "How do the experimental results compare across these papers? "
        "Which method performs best and under what conditions? "
        "Are the benchmarks fair and comparable?"
    ),
    "Datasets and evaluation": (
        "What datasets, baselines, and metrics does each paper use? "
        "Are the evaluation protocols comparable across papers? "
        "Do any papers use weak baselines or cherry-picked results?"
    ),
    "Practical implementation": (
        "Which paper's approach would be most practical to implement in a real system? "
        "Consider code availability, complexity, dependencies, and compute requirements."
    ),
    "Compute and efficiency": (
        "Compare the compute requirements and efficiency of the methods. "
        "How do they trade off accuracy vs speed? "
        "Which would be most suitable for resource-constrained settings?"
    ),
    "Limitations and gaps": (
        "What limitations does each paper acknowledge? "
        "What gaps or weaknesses are not acknowledged but are apparent? "
        "Which claims are least supported by the evidence?"
    ),
    "Future work and open problems": (
        "What open problems and future directions do these papers identify? "
        "Where is there consensus on important next steps? "
        "What promising directions are overlooked?"
    ),
    "Contradictions and disagreements": (
        "Are there any contradictory findings or claims between these papers? "
        "Where do they disagree, and which side has stronger evidence?"
    ),
    "Architectural comparison": (
        "Compare the architectures and system designs proposed in these papers. "
        "What are the key components, how are they connected, and why were those choices made?"
    ),
    "Assumptions and validity": (
        "What core assumptions does each paper make? "
        "Are those assumptions reasonable and clearly stated? "
        "How would the conclusions change if an assumption were violated?"
    ),
    "Reproducibility assessment": (
        "Assess the reproducibility of each paper. "
        "Are implementation details, hyperparameters, and data processing steps clearly described? "
        "Which paper would be easiest to reproduce?"
    ),
}


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

    # Prompt template dropdown
    template_choice = st.selectbox(
        "Prompt template",
        options=list(GENERIC_PROMPTS.keys()),
        index=0,
    )

    # Pre-fill the text area from the selected template
    template_text = GENERIC_PROMPTS[template_choice]
    query = st.text_area(
        "Question",
        value=template_text,
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

    # Load active context for guiding the analysis
    active_ctx = {}
    if "active_context_id" in st.session_state and st.session_state.active_context_id:
        active_ctx = ctx.get_context(project_id, st.session_state.active_context_id) or {}

    with st.spinner("Loading papers and analyzing..."):
        # Gather all triage reports and metadata
        paper_contexts = []
        for pid in paper_ids:
            data = storage.read_paper(project_id, pid)
            meta = data.get("metadata_yaml", "")
            triage = data.get("triage_md", "")
            paper_contexts.append(f"--- PAPER: {pid} ---\nMETADATA:\n{meta}\n\nTRIAGE:\n{triage[:3000]}")

        combined = "\n\n".join(paper_contexts)

        context_block = ""
        if active_ctx:
            parts = []
            if active_ctx.get("goal"):
                parts.append(f"Research Goal: {active_ctx['goal']}")
            if active_ctx.get("milestone"):
                parts.append(f"Milestone: {active_ctx['milestone']}")
            if active_ctx.get("phase"):
                parts.append(f"Phase: {active_ctx['phase']}")
            open_decisions = active_ctx.get("open_decisions", [])
            if open_decisions:
                parts.append("Open Decisions: " + "; ".join(open_decisions))
            if parts:
                context_block = "\n".join(parts)

        system = f"""\
You are comparing research papers for an ML engineer. Given the paper summaries below, answer the user's comparative question.
Be specific. Use numbers if the papers provide them. If a paper doesn't provide relevant information, say so.
Structure your answer clearly. Use a table if comparing multiple metrics across papers.

{f'''PROJECT CONTEXT:
{context_block}

Tailor your analysis to the project goal, milestone, and open decisions above.''' if context_block else ""}
"""

        user = f"""\
PAPERS IN LIBRARY:
{combined}

USER QUESTION:
{query}
"""

        response = llm_call(system, user)
        st.markdown(response)
