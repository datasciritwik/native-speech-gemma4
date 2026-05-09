import yaml

from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from .state import TriageReport, Anatomy, ActionPlan, ScreenerResult

DATA_ROOT = Path.home() / ".paper-agent"


def paper_dir(project_id: str, paper_id: str) -> Path:
    return DATA_ROOT / "projects" / project_id / "library" / paper_id


def paper_exists(project_id: str, paper_id: str) -> bool:
    return (paper_dir(project_id, paper_id) / "metadata.yaml").exists()


def list_papers(project_id: str) -> list[dict]:
    lib = DATA_ROOT / "projects" / project_id / "library"
    if not lib.exists():
        return []
    papers = []
    for d in sorted(lib.iterdir(), reverse=True):
        meta_path = d / "metadata.yaml"
        if meta_path.exists():
            with open(meta_path) as f:
                papers.append(yaml.safe_load(f))
    return papers


# ---- Metadata ----

def write_metadata(
    project_id: str,
    paper_id: str,
    title: str,
    authors: list[str],
    url: Optional[str] = None,
    year: Optional[int] = None,
    code_url: Optional[str] = None,
    tags: Optional[list[str]] = None,
) -> None:
    d = paper_dir(project_id, paper_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "figures").mkdir(exist_ok=True)
    meta = {
        "paper_id": paper_id,
        "title": title,
        "authors": authors,
        "year": year,
        "url": url,
        "code_url": code_url,
        "ingested": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "tags": tags or [],
        "verdict": None,
        "verdict_confidence": None,
        "trigger_condition": None,
    }
    with open(d / "metadata.yaml", "w") as f:
        yaml.dump(meta, f, default_flow_style=False, sort_keys=False)


def update_metadata_verdict(
    project_id: str, paper_id: str, verdict: str, confidence: str, trigger: Optional[str] = None
) -> None:
    path = paper_dir(project_id, paper_id) / "metadata.yaml"
    with open(path) as f:
        meta = yaml.safe_load(f)
    meta["verdict"] = verdict
    meta["verdict_confidence"] = confidence
    meta["trigger_condition"] = trigger
    with open(path, "w") as f:
        yaml.dump(meta, f, default_flow_style=False, sort_keys=False)


# ---- Stage Outputs ----

def write_screener(project_id: str, paper_id: str, result: ScreenerResult) -> None:
    path = paper_dir(project_id, paper_id) / "screener.yaml"
    with open(path, "w") as f:
        yaml.dump(dict(result), f, default_flow_style=False, sort_keys=False)


def write_anatomy(project_id: str, paper_id: str, anatomy: Anatomy) -> None:
    path = paper_dir(project_id, paper_id) / "anatomy.md"
    path.write_text(_format_anatomy_md(anatomy))


def write_triage(project_id: str, paper_id: str, triage: TriageReport) -> None:
    path = paper_dir(project_id, paper_id) / "triage.md"
    path.write_text(_format_triage_md(triage))


def write_action(project_id: str, paper_id: str, action: ActionPlan) -> None:
    path = paper_dir(project_id, paper_id) / "action.md"
    path.write_text(_format_action_md(action))


def write_limitations(project_id: str, paper_id: str, limitations: str) -> None:
    path = paper_dir(project_id, paper_id) / "limitations.md"
    path.write_text(f"# Limitations\n\n{limitations}")


def write_transformations(project_id: str, paper_id: str, transformations: dict) -> None:
    path = paper_dir(project_id, paper_id) / "transformations.md"
    parts = ["# Transformations\n"]
    for key, val in transformations.items():
        parts.append(f"## {key}\n\n{val}\n")
    path.write_text("\n".join(parts))


# ---- Read back ----

def read_paper(project_id: str, paper_id: str) -> dict:
    d = paper_dir(project_id, paper_id)
    result = {}
    for fname in ["metadata.yaml", "screener.yaml", "triage.md", "anatomy.md",
                   "action.md", "limitations.md", "transformations.md"]:
        fp = d / fname
        if fp.exists():
            result[fname.replace(".", "_")] = fp.read_text()
    return result


# ---- Archive ----

def archive_paper(project_id: str, paper_id: str, reason: str) -> None:
    src = paper_dir(project_id, paper_id)
    if not src.exists():
        return
    archive_dir = DATA_ROOT / "archive" / project_id / paper_id
    archive_dir.parent.mkdir(parents=True, exist_ok=True)
    import shutil
    shutil.move(str(src), str(archive_dir))
    (archive_dir / "archive_reason.txt").write_text(reason)


# ---- Markdown formatters ----

def _format_anatomy_md(a: Anatomy) -> str:
    raw = a.get("raw_markdown", "")
    if raw:
        return raw  # use the full LLM response — it has the best formatting
    lines = ["# Anatomy\n"]
    lines.append("## Architecture Blocks\n")
    for block in a.get("architecture_blocks", []):
        lines.append(f"- {block}")
    lines.append("\n## Loss Functions\n")
    for lf in a.get("loss_functions", []):
        lines.append(f"- {lf}")
    lines.append("\n## Key Tables\n")
    for t in a.get("key_tables", []):
        lines.append(f"- {t}")
    return "\n".join(lines)


def _format_triage_md(t: TriageReport) -> str:
    return f"""# Triage Report

## 1. I/O Signature
{t.get("io_signature", "")}

## 2. Novelty
{t.get("novelty", "")}

## 3. Cost Estimate
{t.get("cost_estimate", "")}

## 4. Baselines Beaten
{t.get("baselines_beaten", "")}

## 5. Baselines Missing
{t.get("baselines_missing", "")}

## 6. Ablations That Mattered
{t.get("ablations_that_mattered", "")}

## 7. Failure Modes & Assumptions
{t.get("failures_and_assumptions", "")}

## 8. Integration Difficulty
{t.get("integration_difficulty", "")}
"""


def _format_action_md(a: ActionPlan) -> str:
    verdict_emoji = {
        "implement": "🟩 IMPLEMENT NOW",
        "monitor": "🟨 MONITOR",
        "read_deeper": "🟦 READ DEEPER",
        "ignore": "⬜ IGNORE",
    }
    lines = [f"# Verdict: {verdict_emoji.get(a.get('verdict', ''), a.get('verdict', ''))}\n"]
    lines.append(f"## Summary\n{a.get('summary', '')}\n")
    steps = a.get("concrete_steps", [])
    if steps:
        lines.append("## Concrete Steps\n")
        for i, step in enumerate(steps, 1):
            lines.append(f"{i}. {step}")
        lines.append("")
    if a.get("trigger_condition"):
        lines.append(f"## Trigger Condition\n{a['trigger_condition']}\n")
    if a.get("scoped_reading"):
        lines.append(f"## Scoped Reading\n{a['scoped_reading']}\n")
    return "\n".join(lines)
