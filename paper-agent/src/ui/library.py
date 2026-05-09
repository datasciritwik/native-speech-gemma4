"""Streamlit component: Paper library view."""

import streamlit as st
from .. import storage
from .. import context as ctx

VERDICT_EMOJI = {
    "implement": "🟩",
    "monitor": "🟨",
    "read_deeper": "🟦",
    "ignore": "⬜",
    None: "⬜",
}


def render_library(project_id: str) -> None:
    """Render the full library view with paper list and summary stats."""

    st.markdown("## 📚 Library")

    papers = storage.list_papers(project_id)

    if not papers:
        st.info("No papers ingested yet. Drop a PDF in the sidebar to get started.")
        return

    # Stats row
    verdicts = {}
    for p in papers:
        v = p.get("verdict") or "unknown"
        verdicts[v] = verdicts.get(v, 0) + 1

    cols = st.columns(5)
    cols[0].metric("Total", len(papers))
    cols[1].metric("🟩 Implement", verdicts.get("implement", 0))
    cols[2].metric("🟨 Monitor", verdicts.get("monitor", 0))
    cols[3].metric("🟦 Read", verdicts.get("read_deeper", 0))
    cols[4].metric("⬜ Ignore", verdicts.get("ignore", 0))

    st.divider()

    # Search + filter
    col1, col2 = st.columns([3, 1])
    with col1:
        search = st.text_input("Search", placeholder="Filter by title, author, tag...", label_visibility="collapsed")
    with col2:
        verdict_filter = st.selectbox(
            "Verdict",
            ["All", "Implement", "Monitor", "Read Deeper", "Ignore"],
            label_visibility="collapsed",
        )

    # Filter papers
    filtered = _filter_papers(papers, search, verdict_filter)

    # Paper list
    for paper in filtered:
        _render_paper_card(paper, project_id)


def _filter_papers(papers: list[dict], search: str, verdict_filter: str) -> list[dict]:
    result = []
    for p in papers:
        if verdict_filter != "All" and p.get("verdict", "").lower() != verdict_filter.lower().replace(" ", "_"):
            continue
        if search:
            search_lower = search.lower()
            text = f"{p.get('title', '')} {' '.join(p.get('authors', []))} {' '.join(p.get('tags', []))}"
            if search_lower not in text.lower():
                continue
        result.append(p)
    return result


def _render_paper_card(paper: dict, project_id: str) -> None:
    """Render a single paper card in the library list."""
    pid = paper["paper_id"]
    verdict = paper.get("verdict") or "unknown"
    emoji = VERDICT_EMOJI.get(verdict, "⬜")

    with st.container(border=True):
        col1, col2 = st.columns([5, 1])

        with col1:
            st.markdown(f"**{emoji} {paper.get('title', 'Unknown')}**")
            authors = ", ".join(paper.get("authors", [])[:3])
            if len(paper.get("authors", [])) > 3:
                authors += " et al."
            st.caption(f"{authors} — {paper.get('year', '?')}")

            tags = paper.get("tags", [])
            if tags:
                st.caption(" ".join([f"`{t}`" for t in tags]))

        with col2:
            if st.button("Open", key=f"open_{pid}", use_container_width=True):
                st.session_state["view_paper"] = pid
                st.rerun()

        # Ingested date
        st.caption(f"Ingested: {paper.get('ingested', 'unknown')}")
