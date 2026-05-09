from ..state import AgentState, Anatomy
from ..prompts import anatomy as prompts
from .llm import llm_call


def run_anatomy(state: AgentState) -> AgentState:
    """Stage 2: Extract structural anatomy from the paper."""
    raw = state["raw_paper"]

    # Truncate full text to avoid context overflow — anatomy needs the full paper
    # but we keep it within reasonable bounds
    text = raw["full_text"][:20000]

    user = prompts.USER.format(title=raw["title"], full_text=text)
    response = llm_call(prompts.SYSTEM, user)

    state["anatomy"] = _parse_anatomy(response)
    state["current_stage"] = "triage"
    return state


def _parse_anatomy(response: str) -> Anatomy:
    # Return the raw response structured into sections
    sections = {"architecture_blocks": "", "loss_functions": "", "key_tables": "", "ablations": ""}
    current_section = None

    for line in response.split("\n"):
        lower = line.strip().lower()

        if lower.startswith("1.") or "architecture" in lower:
            current_section = "architecture_blocks"
            sections[current_section] = ""
        elif lower.startswith("2.") or "loss function" in lower:
            current_section = "loss_functions"
            sections[current_section] = ""
        elif lower.startswith("3.") or "key table" in lower or "table" in lower[:15]:
            current_section = "key_tables"
            sections[current_section] = ""
        elif lower.startswith("4.") or "ablation" in lower:
            current_section = "ablations"
            sections[current_section] = ""
        elif current_section:
            sections[current_section] += line + "\n"

    return Anatomy(
        architecture_blocks=_split_list(sections["architecture_blocks"]),
        tensor_shapes={},
        loss_functions=_split_list(sections["loss_functions"]),
        key_tables=_split_list(sections["key_tables"]),
        figures_described=[],
        raw_markdown=response,  # preserve the full LLM output
    )


def _split_list(text: str) -> list[str]:
    """Split section text into list items, filtering noise."""
    items = []
    for line in text.split("\n"):
        line = line.strip()
        if line and (line.startswith("-") or line.startswith("*") or line[0].isdigit()):
            items.append(line.lstrip("-* 0123456789.) "))
        elif line and len(line) > 20:
            items.append(line)
    return items[:20]
