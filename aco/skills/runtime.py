"""Execute local ACO skills."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import uuid4

from aco.skills.contracts import SkillManifest
from aco.skills.registry import default_skills_dir, discover_skills


def load_skill_callable(*, manifest: SkillManifest, skill_dir: Path):
    module_name, function_name = manifest.entrypoint.split(":", 1)
    module_path = skill_dir / f"{module_name}.py"
    if not module_path.exists():
        raise FileNotFoundError(f"skill module not found: {module_path}")

    module = load_module_from_path(module_path)
    handler = getattr(module, function_name, None)
    if handler is None:
        raise AttributeError(f"skill function not found: {manifest.entrypoint}")
    return handler


def load_module_from_path(module_path: Path) -> ModuleType:
    module_id = f"aco_skill_{module_path.stem}_{uuid4().hex}"
    spec = importlib.util.spec_from_file_location(module_id, module_path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load skill module: {module_path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def run_skill(*, manifest: SkillManifest, skill_dir: Path, context: dict) -> dict:
    handler = load_skill_callable(manifest=manifest, skill_dir=skill_dir)
    result = handler(context)
    if not isinstance(result, dict):
        raise TypeError("skill handler must return a dict")
    return result


def find_routing_skill(*, policy: str, skills_dir: str | Path | None = None) -> dict | None:
    for item in discover_skills(skills_dir, skill_type="routing_policy"):
        manifest = item["manifest"]
        if manifest.policy == policy or manifest.name == f"route_{policy}":
            return item
    return None


def apply_routing_skill(
    *,
    policy: str,
    candidates: list[dict],
    estimated_usage: dict,
    skills_dir: str | Path | None = None,
) -> dict:
    skill_dir_root = Path(skills_dir) if skills_dir is not None else default_skills_dir()
    skill = find_routing_skill(policy=policy, skills_dir=skill_dir_root)
    if skill is None:
        return {"candidates": candidates, "skill": None}

    context = {
        "policy": policy,
        "estimated_usage": estimated_usage,
        "candidates": candidates,
    }
    result = run_skill(manifest=skill["manifest"], skill_dir=skill["skill_dir"], context=context)
    ranked_ids = result.get("ranked_provider_ids", [])
    if not ranked_ids:
        return {"candidates": candidates, "skill": skill_payload(skill, result)}

    rank = {provider_id: index for index, provider_id in enumerate(ranked_ids)}
    reordered = sorted(
        candidates,
        key=lambda item: rank.get(item["provider"]["provider_id"], len(rank)),
    )
    return {"candidates": reordered, "skill": skill_payload(skill, result)}


def skill_payload(skill: dict, result: dict) -> dict:
    manifest = skill["manifest"]
    return {
        "name": manifest.name,
        "version": manifest.version,
        "type": manifest.type,
        "policy": manifest.policy,
        "reason": result.get("reason", ""),
    }

