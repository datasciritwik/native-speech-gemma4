import uuid
from pathlib import Path
from typing import Optional

import yaml

DATA_ROOT = Path.home() / ".paper-agent"


def _contexts_path(project_id: str) -> Path:
    return DATA_ROOT / "projects" / project_id / "contexts.yaml"


def _migrate_legacy_context(project_id: str) -> Optional[dict]:
    """Migrate old context.md to the new contexts.yaml format. Returns the migrated context or None."""
    old_path = DATA_ROOT / "projects" / project_id / "context.md"
    if not old_path.exists():
        return None

    text = old_path.read_text()
    fm = {}
    body = ""
    if text.startswith("---"):
        parts = text.split("---", 2)
        if len(parts) >= 3:
            fm = yaml.safe_load(parts[1]) or {}
            body = parts[2].lstrip("\n")

    ctx = {
        "id": "default",
        "name": "Default Context",
        "goal": fm.get("project", ""),
        "milestone": fm.get("milestone", ""),
        "phase": fm.get("phase", ""),
        "open_decisions": fm.get("open_decisions", []),
        "notes": body,
    }

    # Save to new format
    _write_contexts(project_id, [ctx])

    # Rename old file instead of deleting
    old_path.rename(old_path.with_suffix(".md.bak"))
    return ctx


def list_contexts(project_id: str) -> list[dict]:
    """Return all contexts for a project, migrating legacy if needed."""
    path = _contexts_path(project_id)
    if not path.exists():
        migrated = _migrate_legacy_context(project_id)
        if migrated:
            return [migrated]
        return []

    with open(path) as f:
        return yaml.safe_load(f) or []


def get_context(project_id: str, context_id: str) -> Optional[dict]:
    for c in list_contexts(project_id):
        if c.get("id") == context_id:
            return c
    return None


def save_context(project_id: str, context: dict) -> None:
    """Create or update a context. If context has no 'id', a new one is created."""
    contexts = list_contexts(project_id)

    if "id" not in context:
        context["id"] = uuid.uuid4().hex[:8]
        context.setdefault("name", "New Context")
        context.setdefault("goal", "")
        context.setdefault("milestone", "")
        context.setdefault("phase", "")
        context.setdefault("open_decisions", [])
        context.setdefault("notes", "")
        contexts.append(context)
    else:
        for i, c in enumerate(contexts):
            if c.get("id") == context["id"]:
                contexts[i] = context
                break
        else:
            contexts.append(context)

    _write_contexts(project_id, contexts)


def delete_context(project_id: str, context_id: str) -> None:
    contexts = [c for c in list_contexts(project_id) if c.get("id") != context_id]
    _write_contexts(project_id, contexts)


def _write_contexts(project_id: str, contexts: list[dict]) -> None:
    path = _contexts_path(project_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w") as f:
        yaml.dump(contexts, f, default_flow_style=False, sort_keys=False, allow_unicode=True)


# ---- Kept for backward compat with existing callers ----

def load_context(project_id: str) -> dict:
    """Load the first context (backward compat)."""
    contexts = list_contexts(project_id)
    if not contexts:
        return {}
    c = contexts[0]
    return {
        "project": c.get("goal", ""),
        "milestone": c.get("milestone", ""),
        "phase": c.get("phase", ""),
        "open_decisions": c.get("open_decisions", []),
    }


def load_config() -> dict:
    config_path = DATA_ROOT / "config.yaml"
    if config_path.exists():
        with open(config_path) as f:
            return yaml.safe_load(f)
    return {}


def load_decisions(project_id: str) -> dict:
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

    body = context.pop("_body", "")
    _write_frontmatter(
        project_dir / "context.md",
        context,
        body or "Edit this file to update your project context.",
    )

    _write_frontmatter(
        project_dir / "decisions.md",
        {"open_decisions": context.get("open_decisions", []),
         "locked_decisions": context.get("locked_decisions", [])},
        "# Decision Log\n\n## Open Decisions\n\n## Locked Decisions\n",
    )

    _write_frontmatter(
        project_dir / "knowledge.md",
        {"concepts_exposed": [], "papers_read": [], "gaps": []},
        "# Knowledge State\n\n## Concepts Exposed\n\n## Papers Read\n\n## Gaps Identified\n",
    )


def save_context_file(project_id: str, context: dict) -> None:
    """Update a project's context card frontmatter (legacy path)."""
    path = DATA_ROOT / "projects" / project_id / "context.md"
    current = path.read_text() if path.exists() else ""
    body = _body_after_frontmatter(current)
    _write_frontmatter(path, context, body)


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


def _write_frontmatter(path: Path, frontmatter: dict, body: str) -> None:
    fm = yaml.dump(frontmatter, default_flow_style=False, sort_keys=False).strip()
    path.write_text(f"---\n{fm}\n---\n\n{body}")
