from typing import TypedDict, Literal, Optional, NotRequired


class ScreenerResult(TypedDict):
    relevance: Literal["relevant", "irrelevant", "paradigm_shift"]
    urgency: Literal["high", "medium", "low"]
    reason: str


class Anatomy(TypedDict):
    architecture_blocks: list[str]
    tensor_shapes: dict[str, str]
    loss_functions: list[str]
    key_tables: list[str]
    figures_described: list[str]
    raw_markdown: str  # full LLM response preserved as markdown


class TriageReport(TypedDict):
    io_signature: str
    novelty: str
    cost_estimate: str
    baselines_beaten: str
    baselines_missing: str
    failures_and_assumptions: str
    ablations_that_mattered: str
    integration_difficulty: str


class ActionPlan(TypedDict):
    verdict: Literal["implement", "monitor", "read_deeper", "ignore"]
    summary: str
    concrete_steps: list[str]
    trigger_condition: Optional[str]
    scoped_reading: Optional[str]


class RawPaper(TypedDict):
    title: str
    authors: list[str]
    year: Optional[int]
    url: Optional[str]
    abstract: str
    introduction: str
    full_text: str
    figures: list[str]  # file paths to extracted figure images
    tables: list[str]   # markdown table strings


class AgentState(TypedDict):
    paper_id: str
    project_id: str
    pdf_path: str
    raw_paper: NotRequired[RawPaper]
    screener: NotRequired[ScreenerResult]
    anatomy: NotRequired[Anatomy]
    triage: NotRequired[TriageReport]
    limitations: NotRequired[str]
    transformations: NotRequired[dict]
    verdict: NotRequired[ActionPlan]
    error: NotRequired[Optional[str]]
    current_stage: str
