"""Atomic, resumable run-artifact storage with dependency hashes."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any

from .config import StudioConfig, default_run_root
from .models import (
    AgentCallRecord,
    ArtifactRecord,
    RunEvent,
    RunManifest,
    StageState,
    utc_now,
)

STAGES = [
    "clarification",
    "brief_approval",
    "research",
    "extraction",
    "pack_design",
    "study_guide",
    "item_authoring",
    "visual_planning",
    "image_generation",
    "validation",
    "semantic_review",
    "export",
]

STAGE_EXECUTORS = {
    "clarification": "clarifier",
    "brief_approval": "requester",
    "research": "researcher",
    "extraction": "extractor",
    "study_guide": "guide_author",
    "pack_design": "pack_designer",
    "item_authoring": "item_author",
    "visual_planning": "visual_director",
    "image_generation": "image_generator",
    "validation": "deterministic_validator",
    "semantic_review": "reviewer",
    "export": "packager",
}

STAGE_NAMES = {
    "clarification": "Idea clarification",
    "brief_approval": "Brief approval",
    "research": "Grounded research",
    "extraction": "Evidence extraction",
    "study_guide": "Study-guide writing",
    "pack_design": "Lesson and item blueprint",
    "item_authoring": "Seed-item authoring",
    "visual_planning": "Instructional visual planning",
    "image_generation": "Image generation",
    "validation": "Deterministic validation",
    "semantic_review": "Independent semantic review",
    "export": "Portable bundle export",
}


def slugify(value: str, fallback: str = "knowledge-pack") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return slug[:64] or fallback


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


class ArtifactStore:
    def __init__(
        self,
        root: str | Path | None = None,
        event_sink: Callable[[RunEvent], None] | None = None,
    ):
        self.root = Path(root) if root else default_run_root()
        self.event_sink = event_sink
        self.root.mkdir(parents=True, exist_ok=True)

    def _notify(self, event: RunEvent | None) -> None:
        """Send live progress to an optional notebook/UI sink without risking the run."""

        if event is None or self.event_sink is None:
            return
        try:
            self.event_sink(event)
        except Exception:
            # Display callbacks are observational. A broken renderer must never fail authoring.
            pass

    def create_run(self, idea: str, config: StudioConfig, mock: bool) -> RunManifest:
        stamp = utc_now().replace(":", "").replace("-", "").replace("+00:00", "z").lower()
        run_id = f"{slugify(idea)[:32]}-{stamp[:15]}-{uuid.uuid4().hex[:6]}"
        run_dir = self.run_dir(run_id)
        run_dir.mkdir(parents=True, exist_ok=False)
        now = utc_now()
        manifest = RunManifest(
            run_id=run_id,
            created_at=now,
            updated_at=now,
            status="active",
            pipeline_version=config.pipeline_version,
            schema_version=config.schema_version,
            provider=config.provider,
            mock=mock,
            stages={name: StageState.NOT_STARTED for name in STAGES},
            artifacts={},
            agent_calls=[],
            events=[],
        )
        self._write_json_path(run_dir / "run-manifest.json", manifest.model_dump(mode="json"))
        self.write_json(run_id, "idea", "idea.json", {"idea": idea, "createdAt": now}, [])
        self.write_json(
            run_id,
            "configuration",
            "configuration.json",
            config.model_dump(mode="json"),
            [],
        )
        return self.load_manifest(run_id)

    def run_dir(self, run_id: str) -> Path:
        if not re.fullmatch(r"[a-z0-9][a-z0-9-]{5,120}", run_id):
            raise ValueError("Invalid run ID")
        return self.root / run_id

    def load_manifest(self, run_id: str) -> RunManifest:
        return RunManifest.model_validate(self.read_json(run_id, "run-manifest.json"))

    def save_manifest(self, manifest: RunManifest) -> None:
        manifest.updated_at = utc_now()
        self._write_json_path(
            self.run_dir(manifest.run_id) / "run-manifest.json",
            manifest.model_dump(mode="json"),
        )

    def set_stage(self, run_id: str, stage: str, state: StageState) -> None:
        manifest = self.load_manifest(run_id)
        if stage not in manifest.stages:
            raise KeyError(f"Unknown stage: {stage}")
        previous_state = manifest.stages[stage]
        manifest.stages[stage] = state
        if state == StageState.FAILED:
            manifest.status = "needs_attention"
        elif state == StageState.RUNNING:
            manifest.status = "active"
        event = None
        if state != previous_state:
            agent, model = self._stage_executor(manifest, stage)
            event = RunEvent(
                at=utc_now(),
                stage=stage,
                state=state,
                message=self._stage_message(stage, state),
                agent=agent,
                model=model,
            )
            manifest.events.append(event)
        self.save_manifest(manifest)
        self._notify(event)

    def invalidate_downstream(self, run_id: str, stage: str) -> None:
        if stage not in STAGES:
            return
        manifest = self.load_manifest(run_id)
        for later in STAGES[STAGES.index(stage) + 1 :]:
            if manifest.stages[later] == StageState.COMPLETE:
                manifest.stages[later] = StageState.STALE
        self.save_manifest(manifest)

    def record_call(self, run_id: str, call: AgentCallRecord) -> None:
        manifest = self.load_manifest(run_id)
        manifest.agent_calls.append(call)
        pipeline_stage = next(
            (stage for stage, agent in STAGE_EXECUTORS.items() if agent == call.agent),
            call.stage,
        )
        usage: list[str] = []
        if call.input_tokens is not None:
            usage.append(f"{call.input_tokens:,} input tokens")
        if call.output_tokens is not None:
            usage.append(f"{call.output_tokens:,} output tokens")
        if call.tool_calls:
            usage.append(f"{call.tool_calls} tool call{'s' if call.tool_calls != 1 else ''}")
        suffix = f" ({', '.join(usage)})" if usage else ""
        event = RunEvent(
            at=call.created_at,
            stage=pipeline_stage,
            state=StageState.RUNNING,
            message=f"{call.agent} returned a provider response{suffix}.",
            agent=call.agent,
            model=call.model,
        )
        manifest.events.append(event)
        self.save_manifest(manifest)
        self._notify(event)

    def record_event(
        self,
        run_id: str,
        stage: str,
        state: StageState,
        message: str,
        agent: str | None = None,
        model: str | None = None,
    ) -> None:
        """Append a bounded activity entry without changing stage state."""

        manifest = self.load_manifest(run_id)
        event = RunEvent(
            at=utc_now(),
            stage=stage,
            state=state,
            message=message,
            agent=agent,
            model=model,
        )
        manifest.events.append(event)
        manifest.events = manifest.events[-500:]
        self.save_manifest(manifest)
        self._notify(event)

    @staticmethod
    def _stage_message(stage: str, state: StageState) -> str:
        label = STAGE_NAMES[stage]
        if state == StageState.RUNNING:
            return f"{label} started."
        if state == StageState.WAITING_APPROVAL:
            return f"{label} is waiting for requester review and approval."
        if state == StageState.COMPLETE:
            return f"{label} completed."
        if state == StageState.FAILED:
            return f"{label} needs attention. Review the error or download diagnostics."
        if state == StageState.STALE:
            return f"{label} became stale after an upstream change."
        return f"{label} has not started."

    def _stage_executor(self, manifest: RunManifest, stage: str) -> tuple[str | None, str | None]:
        agent = STAGE_EXECUTORS.get(stage)
        if not agent:
            return None, None
        if manifest.mock and agent not in {"requester", "deterministic_validator", "packager"}:
            return agent, "mock-deterministic"
        if agent == "image_generator":
            try:
                config = StudioConfig.model_validate(
                    self.read_json(manifest.run_id, "configuration.json")
                )
                return agent, config.image_model
            except Exception:
                return agent, None
        try:
            config = StudioConfig.model_validate(
                self.read_json(manifest.run_id, "configuration.json")
            )
            configured = config.agents.get(agent)
            return agent, configured.model if configured else None
        except Exception:
            return agent, None

    def write_json(
        self,
        run_id: str,
        name: str,
        relative_path: str,
        data: Any,
        input_hashes: list[str],
        producer: str | None = None,
    ) -> ArtifactRecord:
        payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
        return self._write_artifact(
            run_id, name, relative_path, payload, input_hashes, producer or name
        )

    def write_text(
        self,
        run_id: str,
        name: str,
        relative_path: str,
        text: str,
        input_hashes: list[str],
        producer: str | None = None,
    ) -> ArtifactRecord:
        return self._write_artifact(
            run_id,
            name,
            relative_path,
            text.encode("utf-8"),
            input_hashes,
            producer or name,
        )

    def write_bytes(
        self,
        run_id: str,
        name: str,
        relative_path: str,
        payload: bytes,
        input_hashes: list[str],
        producer: str | None = None,
    ) -> ArtifactRecord:
        return self._write_artifact(
            run_id, name, relative_path, payload, input_hashes, producer or name
        )

    def _write_artifact(
        self,
        run_id: str,
        name: str,
        relative_path: str,
        payload: bytes,
        input_hashes: list[str],
        producer: str,
    ) -> ArtifactRecord:
        run_dir = self.run_dir(run_id).resolve()
        target = (run_dir / relative_path).resolve()
        if run_dir not in target.parents:
            raise ValueError("Artifact path escapes the run directory")
        target.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(target, payload)
        record = ArtifactRecord(
            name=name,
            relative_path=relative_path,
            sha256=sha256_bytes(payload),
            created_at=utc_now(),
            producer=producer,
            input_hashes=input_hashes,
        )
        manifest = self.load_manifest(run_id)
        manifest.artifacts[name] = record
        self.save_manifest(manifest)
        return record

    def read_json(self, run_id: str, relative_path: str) -> Any:
        return json.loads((self.run_dir(run_id) / relative_path).read_text(encoding="utf-8"))

    def read_text(self, run_id: str, relative_path: str) -> str:
        return (self.run_dir(run_id) / relative_path).read_text(encoding="utf-8")

    def artifact_hashes(self, run_id: str, *names: str) -> list[str]:
        manifest = self.load_manifest(run_id)
        return [manifest.artifacts[name].sha256 for name in names if name in manifest.artifacts]

    def artifact_path(self, run_id: str, name: str) -> Path:
        manifest = self.load_manifest(run_id)
        return self.run_dir(run_id) / manifest.artifacts[name].relative_path

    def list_runs(self) -> list[str]:
        if not self.root.exists():
            return []
        return sorted(
            [path.name for path in self.root.iterdir() if (path / "run-manifest.json").is_file()],
            reverse=True,
        )

    @staticmethod
    def _atomic_write(path: Path, payload: bytes) -> None:
        with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
            handle.write(payload)
            temp_name = handle.name
        os.replace(temp_name, path)

    def _write_json_path(self, path: Path, data: Any) -> None:
        payload = json.dumps(data, indent=2, ensure_ascii=False, sort_keys=True).encode("utf-8")
        path.parent.mkdir(parents=True, exist_ok=True)
        self._atomic_write(path, payload)
