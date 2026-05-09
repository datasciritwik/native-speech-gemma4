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
)

# ---- Session State Init ----
if "view_paper" not in st.session_state:
    st.session_state.view_paper = None

if "ingestion_active" not in st.session_state:
    st.session_state.ingestion_active = False

# ---- Sidebar: Project selector + upload ----
with st.sidebar:
    st.markdown("# 📚 Paper Agent")

    projects = ctx.list_projects()
    if not projects:
        st.warning("No projects found. Create one first.")
        st.stop()

    project_id = st.selectbox("Project", projects, key="project_selector")

    st.divider()
    render_upload(project_id)
    render_ingestion_progress()

    st.divider()

    with st.expander("Project Context"):
        try:
            project_ctx = ctx.load_context(project_id)
            st.markdown(f"**Goal:** {project_ctx.get('project', 'N/A')}")
            st.markdown(f"**Milestone:** {project_ctx.get('milestone', 'N/A')}")
            st.markdown(f"**Phase:** {project_ctx.get('phase', 'N/A')}")

            open_dec = project_ctx.get("open_decisions", [])
            if open_dec:
                st.markdown("**Open Decisions:**")
                for d in open_dec:
                    st.markdown(f"- {d}")
        except Exception:
            st.caption("No context loaded.")

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

