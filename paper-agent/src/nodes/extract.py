import re
from pathlib import Path

import fitz  # pymupdf

from ..state import AgentState, RawPaper


def extract_pdf(state: AgentState) -> AgentState:
    """Extract text from a PDF. Sets raw_paper in state."""
    pdf_path = state["pdf_path"]
    doc = fitz.open(pdf_path)

    full_text_parts = []
    for page in doc:
        full_text_parts.append(page.get_text())

    full_text = "\n\n".join(full_text_parts)
    doc.close()

    # Heuristic extraction of title, abstract, introduction
    title = _extract_title(full_text)
    abstract = _extract_section(full_text, ["abstract"])
    introduction = _extract_section(full_text, ["introduction", "1. introduction", "1 introduction"])

    raw: RawPaper = {
        "title": title,
        "authors": [],
        "year": None,
        "url": None,
        "abstract": abstract,
        "introduction": introduction or full_text[:3000],
        "full_text": full_text,
        "figures": [],
        "tables": [],
    }

    state["raw_paper"] = raw
    state["current_stage"] = "screener"
    return state


def _extract_title(text: str) -> str:
    lines = text.strip().split("\n")
    for line in lines[:10]:
        line = line.strip()
        if len(line) > 10 and len(line) < 300:
            return line
    return "Unknown Title"


def _extract_section(text: str, section_names: list[str]) -> str:
    """Extract text of the first matching section by heading."""
    text_lower = text.lower()
    for name in section_names:
        pattern = rf"(?:^|\n)\s*{re.escape(name)}\s*\n"
        match = re.search(pattern, text_lower)
        if match:
            start = match.end()
            # Find next section heading
            next_section = re.search(r"\n\s*(?:\d+\.?\s+)?[A-Z][a-z]+(?:\s+[A-Z][a-z]+)?\s*\n", text[start:])
            if next_section:
                return text[start : start + next_section.start()].strip()
            return text[start:start + 5000].strip()
    return ""
