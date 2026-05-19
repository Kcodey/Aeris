"""Skill registry: discover skills cheaply, load them only when needed."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Optional


@dataclass
class SkillManifest:
    name: str
    description: str
    path: Path


@dataclass
class SkillDocument:
    manifest: SkillManifest
    body: str


class SkillRegistry:
    """Registry for SKILL.md files.

    Loads all skill manifests at init (cheap), defers full body loading
    until load_full_text() is called.
    """

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir.resolve()
        self.documents: Dict[str, SkillDocument] = {}
        self._load_all()

    def _load_all(self) -> None:
        if not self.skills_dir.exists():
            return
        for path in sorted(self.skills_dir.rglob("SKILL.md")):
            meta, body = self._parse_frontmatter(path.read_text(encoding="utf-8"))
            name = meta.get("name", path.parent.name)
            description = meta.get("description", "No description")
            manifest = SkillManifest(name=name, description=description, path=path)
            self.documents[name] = SkillDocument(manifest=manifest, body=body.strip())

    def _parse_frontmatter(self, text: str) -> tuple[dict, str]:
        match = re.match(r"^---\n(.*?)\n---\n(.*)", text, re.DOTALL)
        if not match:
            return {}, text
        meta = {}
        for line in match.group(1).strip().splitlines():
            if ":" not in line:
                continue
            key, value = line.split(":", 1)
            meta[key.strip()] = value.strip()
        return meta, match.group(2)

    def describe_available(self) -> str:
        if not self.documents:
            return "(no skills available)"
        lines = []
        for name in sorted(self.documents):
            manifest = self.documents[name].manifest
            lines.append(f"- {manifest.name}: {manifest.description}")
        return "\n".join(lines)

    def load_full_text(self, name: str) -> str:
        document = self.documents.get(name)
        if not document:
            known = ", ".join(sorted(self.documents)) or "(none)"
            return f"Error: Unknown skill '{name}'. Available skills: {known}"
        return (
            f'<skill name="{document.manifest.name}">\n'
            f"{document.body}\n"
            "</skill>"
        )

    def list_skills(self) -> list[str]:
        return sorted(self.documents.keys())


# Global singleton
_registry: Optional[SkillRegistry] = None


def init_skill_registry(skills_dir: Path) -> SkillRegistry:
    """Initialize and return the global skill registry."""
    global _registry
    _registry = SkillRegistry(skills_dir)
    return _registry


def get_skill_registry() -> SkillRegistry:
    """Get the global skill registry singleton.

    Must call init_skill_registry() first during app startup.
    """
    if _registry is None:
        raise RuntimeError("SkillRegistry not initialized. Call init_skill_registry() first.")
    return _registry
