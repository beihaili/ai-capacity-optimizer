"""Discover local ACO skills."""

from __future__ import annotations

import json
from pathlib import Path

from aco.skills.contracts import SkillManifest


def default_skills_dir(data_dir: str | Path | None = None) -> Path:
    if data_dir is not None:
        data_path = Path(data_dir).resolve()
        if data_path.name == "data" and data_path.parent.name == "aco":
            return data_path.parents[1] / "skills"
    return Path(__file__).resolve().parents[2] / "skills"


def discover_skills(
    skills_dir: str | Path | None = None,
    *,
    skill_type: str | None = None,
    enabled_only: bool = True,
) -> list[dict]:
    root = Path(skills_dir) if skills_dir is not None else default_skills_dir()
    if not root.exists():
        return []

    discovered: list[dict] = []
    for manifest_path in sorted(root.glob("*/skill.json")):
        raw = json.loads(manifest_path.read_text(encoding="utf-8"))
        manifest = SkillManifest.from_dict(raw)
        if enabled_only and not manifest.enabled:
            continue
        if skill_type is not None and manifest.type != skill_type:
            continue
        discovered.append(
            {
                "manifest": manifest,
                "skill_dir": manifest_path.parent,
                "manifest_path": manifest_path,
            }
        )
    return discovered


def list_skill_payloads(skills_dir: str | Path | None = None) -> list[dict]:
    payloads = []
    for item in discover_skills(skills_dir):
        manifest = item["manifest"]
        payload = manifest.to_dict()
        payload["path"] = str(item["skill_dir"])
        payloads.append(payload)
    return payloads

