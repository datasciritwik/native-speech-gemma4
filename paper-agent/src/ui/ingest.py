"""Streamlit component: PDF upload and ingestion with progress tracking."""

import os
import tempfile
import time

import streamlit as st

from ..graph import ingestion_graph
from ..state import AgentState


def render_upload(project_id: str) -> None:
    """Render the PDF upload area in the sidebar."""

    st.markdown("### 📄 Upload Paper")

    uploaded = st.file_uploader(
        "Drop a PDF",
        type=["pdf"],
        label_visibility="collapsed",
    )

    if uploaded is not None:
        paper_id = _paper_id_from_filename(uploaded.name)

        if st.button(f"Ingest: {uploaded.name}", type="primary", use_container_width=True):
            _run_ingestion(uploaded, paper_id, project_id)


def render_ingestion_progress() -> None:
    """If there is an active ingestion, show its progress.
    State is driven by session_state.ingestion_* keys."""

    if "ingestion_active" not in st.session_state:
        return

    if not st.session_state.ingestion_active:
        return

    st.divider()
    st.markdown(f"### ⏳ Ingesting: {st.session_state.get('ingestion_paper_id', '')}")

    stages = st.session_state.get("ingestion_stages", [])
    current = st.session_state.get("ingestion_current_stage", "")

    for stage_name, done in stages:
        if done:
            st.markdown(f"✅ {stage_name}")
        elif stage_name == current:
            st.markdown(f"⏳ {stage_name}")
        else:
            st.markdown(f"⬜ {stage_name}")


def _paper_id_from_filename(filename: str) -> str:
    """Derive a paper_id from the filename."""
    base = os.path.splitext(filename)[0]
    # Clean: lowercase, replace spaces/special chars with dashes
    import re
    base = base.lower().strip()
    base = re.sub(r"[^a-z0-9]+", "-", base)
    return base.strip("-")


def _run_ingestion(uploaded_file, paper_id: str, project_id: str) -> None:
    """Execute the full ingestion graph and update session state with progress."""

    # Save uploaded PDF to temp file
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as tmp:
        tmp.write(uploaded_file.read())
        pdf_path = tmp.name

    # Initialize state tracking
    st.session_state.ingestion_active = True
    st.session_state.ingestion_paper_id = paper_id
    st.session_state.ingestion_stages = []
    st.session_state.ingestion_current_stage = "extract"

    # Build initial agent state
    state: AgentState = {
        "paper_id": paper_id,
        "project_id": project_id,
        "pdf_path": pdf_path,
        "current_stage": "extract",
    }

    progress_bar = st.progress(0, text="Starting...")
    stage_names = ["extract", "screen", "anatomy", "triage", "skeptic", "transform", "verdict", "persist"]
    stage_labels = [
        "Extracting PDF",
        "Screening relevance",
        "Extracting architecture",
        "Writing triage report",
        "Skeptic analysis",
        "Generating transformations",
        "Producing verdict",
        "Saving to library",
    ]

    stage_history = []

    try:
        # Run the graph, streaming state updates
        for i, event in enumerate(ingestion_graph.stream(state)):
            for node_name, node_state in event.items():
                progress = (stage_names.index(node_name) + 1) / len(stage_names)
                label_idx = stage_names.index(node_name) if node_name in stage_names else i
                progress_bar.progress(progress, text=stage_labels[label_idx] if label_idx < len(stage_labels) else node_name)

                st.session_state.ingestion_current_stage = node_name
                stage_history.append((node_name, True))
                st.session_state.ingestion_stages = stage_history

        progress_bar.progress(1.0, text="Done!")

        # Clear temp file
        os.unlink(pdf_path)

        st.session_state.ingestion_active = False
        st.success(f"Paper `{paper_id}` ingested successfully!")
        time.sleep(1)
        st.rerun()

    except Exception as e:
        st.session_state.ingestion_active = False
        progress_bar.progress(0, text="Failed")
        st.error(f"Ingestion failed: {e}")
        os.unlink(pdf_path)
