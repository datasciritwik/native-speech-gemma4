import yaml
from pathlib import Path
from typing import Optional

DATA_ROOT = Path.home() / ".paper-agent"


def load_config() -> dict:
    with open(DATA_ROOT / "config.yaml") as f:
        return yaml.safe_load(f)


def load_context(project_id: str) -> dict:
    """Load a project's context card, returning the YAML frontmatter as a dict."""
    path = DATA_ROOT / "projects" / project_id / "context.md"
    if not path.exists():
        raise FileNotFoundError(f"No context found for project '{project_id}' at {path}")
    return _read_frontmatter(path)


def save_context(project_id: str, context: dict) -> None:
    """Update a project's context card frontmatter."""
    path = DATA_ROOT / "projects" / project_id / "context.md"
    current = path.read_text() if path.exists() else ""
    body = _body_after_frontmatter(current)
    _write_with_frontmatter(path, context, body)


def load_decisions(project_id: str) -> dict:
    """Load decisions log, returning frontmatter + markdown body sections."""
    path = DATA_ROOT / "projects" / project_id / "decisions.md"
    if not path.exists():
        return {"open": [], "locked": []}
    return _read_frontmatter(path)


def load_knowledge(project_id: str) -> dict:
    path = DATA_ROOT / "projects" / project_id / "knowledge.md"
    if not path.exists():
        return {"concepts_exposed": [], "papers_read": [], "gaps": []}
    return _read_frontmatter(path)


def project_exists(project_id: str) -> bool:
    return (DATA_ROOT / "projects" / project_id).exists()


def list_projects() -> list[str]:
    projects_dir = DATA_ROOT / "projects"
    if not projects_dir.exists():
        return []
    return [p.name for p in projects_dir.iterdir() if p.is_dir()]


def create_project(project_id: str, context: dict) -> None:
    project_dir = DATA_ROOT / "projects" / project_id
    project_dir.mkdir(parents=True, exist_ok=True)
    (project_dir / "library").mkdir(exist_ok=True)

    context_body = context.pop("_body", "")
    _write_with_frontmatter(
        project_dir / "context.md",
        context,
        context_body or "Edit this file to update your project context.",
    )

    _write_with_frontmatter(
        project_dir / "decisions.md",
        {"open_decisions": context.get("open_decisions", []),
         "locked_decisions": context.get("locked_decisions", [])},
        "# Decision Log\n\n## Open Decisions\n\n## Locked Decisions\n",
    )

    _write_with_frontmatter(
        project_dir / "knowledge.md",
        {"concepts_exposed": [], "papers_read": [], "gaps": []},
        "# Knowledge State\n\n## Concepts Exposed\n\n## Papers Read\n\n## Gaps Identified\n",
    )


def _read_frontmatter(path: Path) -> dict:
    text = path.read_text()
    if not text.startswith("---"):
        return {}
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}
    return yaml.safe_load(parts[1]) or {}


def _body_after_frontmatter(text: str) -> str:
    if not text.startswith("---"):
        return text
    parts = text.split("---", 2)
    return parts[2].lstrip("\n") if len(parts) >= 3 else ""


def _write_with_frontmatter(path: Path, frontmatter: dict, body: str) -> None:
    fm = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body}")
