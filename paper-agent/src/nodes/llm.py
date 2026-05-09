"""Shared LLM helper for all nodes."""

from langchain_deepseek import ChatDeepSeek
from langchain_core.messages import SystemMessage, HumanMessage

from ..context import load_config, load_context


def _build_llm():
    config = load_config()
    llm_config = config["llm"]
    return ChatDeepSeek(
        model=llm_config.get("model", "deepseek-chat"),
        temperature=llm_config.get("temperature", 0.0),
        max_tokens=llm_config.get("max_tokens", 4096),
    )


# Singleton — created once
_llm = None


def get_llm():
    global _llm
    if _llm is None:
        _llm = _build_llm()
    return _llm


def llm_call(system: str, user: str) -> str:
    """Call the LLM with system + user prompts, return text response."""
    llm = get_llm()
    messages = [SystemMessage(content=system), HumanMessage(content=user)]
    response = llm.invoke(messages)
    return response.content


def format_project_context(project_id: str) -> dict:
    """Load the project context card and return formatted strings for prompts."""
    ctx = load_context(project_id)
    return {
        "goal": ctx.get("project", ""),
        "milestone": ctx.get("milestone", ""),
        "open_decisions": ", ".join(ctx.get("open_decisions", [])),
        "locked_decisions": ", ".join(ctx.get("locked_decisions", [])),
        "constraints": str(ctx.get("constraints", {})),
    }
