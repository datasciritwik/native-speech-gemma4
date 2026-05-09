"""Streamlit component: Paper detail view with tabbed reports."""

import streamlit as st
from .. import storage


def render_detail(project_id: str, paper_id: str) -> None:
    """Render the detailed view for a single paper."""

    data = storage.read_paper(project_id, paper_id)

    if not data:
        st.error(f"Paper '{paper_id}' not found.")
        return

    # Back button
    if st.button("← Back to Library"):
        st.session_state.pop("view_paper", None)
        st.rerun()

    # Header from metadata
    meta = _parse_yaml(data.get("metadata_yaml", ""))
    st.markdown(f"## {meta.get('title', paper_id)}")
    st.caption(f"{', '.join(meta.get('authors', []))} — {meta.get('year', '?')}")

    if meta.get("url"):
        st.markdown(f"[arXiv]({meta['url']}) | [Code]({meta.get('code_url', '#')})")

    # Verdict badge
    verdict = meta.get("verdict", "unknown")
    verdict_color = {
        "implement": "green",
        "monitor": "orange",
        "read_deeper": "blue",
        "ignore": "gray",
    }
    st.markdown(
        f"**Verdict:** :{verdict_color.get(verdict, 'gray')}[{verdict.upper().replace('_', ' ')}]"
    )
    st.divider()

    # Tabs
    tabs = st.tabs(["Triage Report", "Anatomy", "Action Plan", "Limitations", "Transformations"])

    with tabs[0]:
        triage_content = data.get("triage_md", "")
        if triage_content:
            st.markdown(triage_content)
        else:
            st.info("No triage report available.")

    with tabs[1]:
        anatomy_content = data.get("anatomy_md", "")
        if anatomy_content:
            st.markdown(anatomy_content)
        else:
            st.info("No anatomy extracted.")

    with tabs[2]:
        action_content = data.get("action_md", "")
        if action_content:
            st.markdown(action_content)
        else:
            st.info("No action plan available.")

    with tabs[3]:
        limitations_content = data.get("limitations_md", "")
        if limitations_content:
            st.markdown(limitations_content)
        else:
            st.info("No limitations analysis available.")

    with tabs[4]:
        transform_content = data.get("transformations_md", "")
        if transform_content:
            st.markdown(transform_content)
        else:
            st.info("No transformations generated.")


def _parse_yaml(text: str) -> dict:
    import yaml
    try:
        return yaml.safe_load(text) or {}
    except Exception:
        return {}
