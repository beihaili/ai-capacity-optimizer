"""Skill manifest contracts."""

from __future__ import annotations

from dataclasses import dataclass


SKILL_TYPES = {"provider", "routing_policy", "optimizer", "relay", "postprocess"}


@dataclass(frozen=True)
class SkillManifest:
    name: str
    version: str
    type: str
    description: str
    entrypoint: str
    inputs: list[str]
    outputs: list[str]
    enabled: bool = True
    policy: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> "SkillManifest":
        manifest = cls(
            name=str(data["name"]),
            version=str(data.get("version", "0.1.0")),
            type=str(data["type"]),
            description=str(data.get("description", "")),
            entrypoint=str(data["entrypoint"]),
            inputs=[str(item) for item in data.get("inputs", [])],
            outputs=[str(item) for item in data.get("outputs", [])],
            enabled=bool(data.get("enabled", True)),
            policy=str(data["policy"]) if data.get("policy") else None,
        )
        manifest.validate()
        return manifest

    def validate(self) -> None:
        if not self.name:
            raise ValueError("skill name is required")
        if self.type not in SKILL_TYPES:
            allowed = ", ".join(sorted(SKILL_TYPES))
            raise ValueError(f"skill type must be one of: {allowed}")
        if ":" not in self.entrypoint:
            raise ValueError("skill entrypoint must use 'module:function'")

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "version": self.version,
            "type": self.type,
            "description": self.description,
            "entrypoint": self.entrypoint,
            "inputs": self.inputs,
            "outputs": self.outputs,
            "enabled": self.enabled,
            "policy": self.policy,
        }

