"""Paper Agent — Streamlit entry point.

Run with: streamlit run src/app.py
"""

import sys
import os

# Allow running directly with `streamlit run src/app.py` from package root
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st

from src import context as ctx
from src.ui.library import render_library
from src.ui.detail import render_detail
from src.ui.ingest import render_upload, render_ingestion_progress
from src.ui.query import render_query


st.set_page_config(
    page_title="Paper Agent",
    page_icon="📚",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Ensure sidebar doesn't eat the main content
st.markdown(
    """
    <style>
    [data-testid="stSidebar"] {
        min-width: 260px;
        max-width: 320px;
    }
    [data-testid="stSidebar"] > div:first-child {
        padding: 1rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---- Session State Init ----
if "view_paper" not in st.session_state:
    st.session_state.view_paper = None

if "ingestion_active" not in st.session_state:
    st.session_state.ingestion_active = False

if "active_context_id" not in st.session_state:
    st.session_state.active_context_id = None

if "show_new_context_form" not in st.session_state:
    st.session_state.show_new_context_form = False


def _render_context_selector(project_id: str) -> None:
    """Render the context dropdown + add/delete buttons."""

    contexts = ctx.list_contexts(project_id)

    if not contexts:
        st.info("No contexts yet. Create one below.")
        if st.button("+ New Context", use_container_width=True):
            st.session_state.show_new_context_form = True
            st.rerun()
        return

    # Build options: first is always the selected one, or pick first
    context_options = {c["id"]: c["name"] for c in contexts}

    # Ensure active_context_id is valid for this project
    if st.session_state.active_context_id not in context_options:
        st.session_state.active_context_id = contexts[0]["id"]

    # Context selector — full width dropdown
    selected_id = st.selectbox(
        "Context",
        options=list(context_options.keys()),
        format_func=lambda cid: context_options[cid],
        index=list(context_options.keys()).index(st.session_state.active_context_id),
        key="context_selector",
        label_visibility="collapsed",
    )
    st.session_state.active_context_id = selected_id

    # Buttons row — wider columns so they don't clip in the sidebar
    bc1, bc2 = st.columns([1, 1])
    with bc1:
        if st.button("＋ New", key="add_context_btn", use_container_width=True, help="Create new context"):
            st.session_state.show_new_context_form = True
            st.rerun()
    with bc2:
        if len(contexts) > 1:
            if st.button("🗑 Delete", key="delete_context_btn", use_container_width=True, help="Delete this context"):
                ctx.delete_context(project_id, selected_id)
                st.session_state.active_context_id = None
                st.rerun()

    # New context form
    if st.session_state.get("show_new_context_form"):
        with st.container(border=True):
            name = st.text_input("Context name", key="new_ctx_name")
            goal = st.text_area("Research goal", key="new_ctx_goal")
            if st.button("Save Context", use_container_width=True):
                if name.strip():
                    ctx.save_context(project_id, {
                        "name": name.strip(),
                        "goal": goal.strip(),
                    })
                    st.session_state.active_context_id = None  # will be set on next render
                    st.session_state.show_new_context_form = False
                    st.rerun()
            if st.button("Cancel", use_container_width=True):
                st.session_state.show_new_context_form = False
                st.rerun()

    # Show current context details
    current = ctx.get_context(project_id, st.session_state.active_context_id)
    if current:
        with st.expander("Context Details", expanded=False):
            new_name = st.text_input("Name", value=current.get("name", ""), key="ctx_edit_name")
            new_goal = st.text_area("Goal", value=current.get("goal", ""), key="ctx_edit_goal")
            new_milestone = st.text_input("Milestone", value=current.get("milestone", ""), key="ctx_edit_milestone")
            new_phase = st.text_input("Phase", value=current.get("phase", ""), key="ctx_edit_phase")

            st.markdown("**Open Decisions:**")
            decisions = list(current.get("open_decisions", []))
            decs_to_remove = []
            for i, d in enumerate(decisions):
                cd1, cd2 = st.columns([4, 1])
                with cd1:
                    decisions[i] = st.text_input(f"Decision {i+1}", value=d, key=f"dec_{i}", label_visibility="collapsed")
                with cd2:
                    if st.button("✕", key=f"rm_dec_{i}", help="Remove decision", use_container_width=True):
                        decs_to_remove.append(i)
            for i in reversed(decs_to_remove):
                decisions.pop(i)

            new_decision = st.text_input("Add decision", key="new_decision", placeholder="New open decision...")

            if st.button("Save Changes", use_container_width=True):
                updated = {
                    "id": current["id"],
                    "name": new_name,
                    "goal": new_goal,
                    "milestone": new_milestone,
                    "phase": new_phase,
                    "open_decisions": [d for d in decisions if d.strip()],
                    "notes": current.get("notes", ""),
                }
                if new_decision.strip():
                    updated["open_decisions"].append(new_decision.strip())
                ctx.save_context(project_id, updated)
                st.rerun()

    st.divider()


# ---- Sidebar: Project selector + upload ----
with st.sidebar:
    st.markdown("# 📚 Paper Agent")

    projects = ctx.list_projects()
    if not projects:
        st.warning("No projects found. Create one first.")
        st.stop()

    project_id = st.selectbox("Project", projects, key="project_selector")

    st.divider()
    _render_context_selector(project_id)
    render_upload(project_id)
    render_ingestion_progress()

# ---- Main Content ----
st.markdown(
    f"<style> .block-container {{ padding-top: 1rem; }} </style>",
    unsafe_allow_html=True,
)

# Navigation
tab_library, tab_query = st.tabs(["Library", "Cross-Paper Query"])

with tab_library:
    if st.session_state.view_paper:
        render_detail(project_id, st.session_state.view_paper)
    else:
        render_library(project_id)

with tab_query:
    render_query(project_id)

