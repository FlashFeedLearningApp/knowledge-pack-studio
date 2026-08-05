"""Versioned runtime and agent configuration."""

from __future__ import annotations

from pathlib import Path

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """A logical specialist's model, credential, and reasoning policy."""

    model: str
    credential: str = "default"
    reasoning_effort: str = "medium"


class StudioConfig(BaseModel):
    """Configuration persisted in a run manifest, never including secret values."""

    pipeline_version: str = "0.2.0.dev0"
    schema_version: str = "0.3.0"
    provider: str = "openai"
    target_item_count: int = Field(default=48, ge=12, le=240)
    max_web_searches: int = Field(default=12, ge=1, le=100)
    image_count_limit: int = Field(default=4, ge=0, le=20)
    agents: dict[str, AgentConfig] = Field(default_factory=lambda: default_agents())
    image_model: str = "gpt-image-2"


def default_agents() -> dict[str, AgentConfig]:
    """Cost-aware starting assignments; every value is editable in the UI."""

    return {
        "clarifier": AgentConfig(model="gpt-5.6-terra", reasoning_effort="medium"),
        "researcher": AgentConfig(model="gpt-5.6-sol", reasoning_effort="high"),
        "extractor": AgentConfig(model="gpt-5.6-terra", reasoning_effort="medium"),
        "guide_author": AgentConfig(model="gpt-5.6-terra", reasoning_effort="medium"),
        "pack_designer": AgentConfig(model="gpt-5.6-terra", reasoning_effort="medium"),
        "item_author": AgentConfig(model="gpt-5.6-terra", reasoning_effort="medium"),
        "visual_director": AgentConfig(model="gpt-5.6-terra", reasoning_effort="low"),
        "reviewer": AgentConfig(model="gpt-5.6-sol", reasoning_effort="high"),
    }


def default_run_root() -> Path:
    """Use Colab's ephemeral disk there; otherwise keep local runs out of source."""

    if Path("/content").is_dir():
        return Path("/content/knowledge-pack-runs")
    return Path.cwd() / "runs"
