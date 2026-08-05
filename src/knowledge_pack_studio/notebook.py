"""Native notebook facade for the resumable Knowledge Pack Studio engine."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from .config import StudioConfig
from .diagnostics import build_diagnostics_bundle, studio_runtime_identity
from .models import RunEvent, StageState, utc_now
from .store import STAGE_NAMES, STAGES, ArtifactStore
from .workflow import StudioWorkflow


def _safe_cell(value: Any) -> str:
    return str(value).replace("|", "\\|").replace("\n", " ")


class NotebookStudio:
    """Small, display-friendly API shared by Colab, Codespaces, and local Jupyter.

    Credentials live only on this Python object. They are passed to the provider for the current
    stage and are never placed in the run manifest, configuration, diagnostics, or export bundle.
    """

    def __init__(
        self,
        run_root: str | Path | None = None,
        *,
        api_key: str | None = None,
        credentials: dict[str, str] | None = None,
        echo_progress: bool = True,
    ) -> None:
        self.credentials = dict(credentials or {})
        if api_key:
            self.credentials["default"] = api_key
        self.echo_progress = echo_progress
        self.current_run_id: str | None = None
        self.store = ArtifactStore(run_root, event_sink=self._on_event)
        self.workflow = StudioWorkflow(self.store)

    @classmethod
    def from_environment(
        cls,
        run_root: str | Path | None = None,
        *,
        secret_name: str = "OPENAI_API_KEY_FF_KP",
        echo_progress: bool = True,
    ) -> NotebookStudio:
        """Create a session using the dedicated environment secret, if present."""

        return cls(
            run_root,
            api_key=os.environ.get(secret_name),
            echo_progress=echo_progress,
        )

    @property
    def live_mode_ready(self) -> bool:
        return bool(self.credentials.get("default"))

    def _on_event(self, event: RunEvent) -> None:
        if not self.echo_progress:
            return
        clock = event.at[11:19] if len(event.at) >= 19 else event.at
        actor = ""
        if event.agent:
            actor = f" · {event.agent}"
            if event.model:
                actor += f" / {event.model}"
        print(f"[{clock}] {event.stage}: {event.message}{actor}", flush=True)

    def _run_id(self, run_id: str | None = None) -> str:
        selected = run_id or self.current_run_id
        if not selected:
            raise RuntimeError("Create or resume a run first")
        return selected

    def create_run(
        self,
        idea: str,
        *,
        config: StudioConfig | None = None,
        mock: bool = False,
    ) -> str:
        if not mock and not self.live_mode_ready:
            raise RuntimeError(
                "Live mode needs OPENAI_API_KEY_FF_KP in the current notebook environment"
            )
        self.current_run_id = self.workflow.create_run(idea, config=config, mock=mock)
        mode = "MOCK — cannot publish" if mock else "LIVE — API charges may apply"
        print(f"Created {self.current_run_id}\nMode: {mode}\nRun folder: {self.run_dir}")
        return self.current_run_id

    def resume(self, run_id: str | None = None) -> str:
        selected = run_id or next(iter(self.store.list_runs()), None)
        if not selected:
            raise RuntimeError(f"No saved runs were found under {self.store.root}")
        self.store.load_manifest(selected)
        self.current_run_id = selected
        print(f"Resumed {selected}\nRun folder: {self.run_dir}")
        return selected

    @property
    def run_dir(self) -> Path:
        return self.store.run_dir(self._run_id())

    def clarify(self, intake: dict[str, Any], run_id: str | None = None):
        return self.workflow.clarify(self._run_id(run_id), intake, self.credentials)

    def clarification_questions(self, run_id: str | None = None) -> list[dict[str, Any]]:
        selected = self._run_id(run_id)
        raw_draft = self.store.read_json(selected, "brief/brief-draft.json")
        from .models import BriefDraft

        draft = BriefDraft.model_validate(raw_draft)
        intake_path = self.store.run_dir(selected) / "brief/intake.json"
        intake = (
            self.store.read_json(selected, "brief/intake.json") if intake_path.is_file() else {}
        )
        upgraded = StudioWorkflow._apply_clarification_gates(draft, intake)
        upgraded_data = upgraded.model_dump(mode="json")
        if upgraded_data != raw_draft:
            self.store.write_json(
                selected,
                "brief_draft",
                "brief/brief-draft.json",
                upgraded_data,
                self.store.artifact_hashes(selected, "idea", "configuration", "intake"),
                "clarification_migration",
            )
        return upgraded_data["clarification_questions"]

    def clarification_state(self, run_id: str | None = None) -> dict[str, Any]:
        selected = self._run_id(run_id)
        path = self.store.run_dir(selected) / "brief/requester-answers.json"
        if not path.is_file():
            return {"answers": {}, "skipped": [], "updated_at": None}
        return self.store.read_json(selected, "brief/requester-answers.json")

    def _save_clarification_state(
        self,
        answers: dict[str, str],
        skipped: list[str],
        run_id: str | None = None,
    ) -> dict[str, Any]:
        selected = self._run_id(run_id)
        state = {
            "answers": answers,
            "skipped": sorted(set(skipped)),
            "updated_at": utc_now(),
        }
        self.store.write_json(
            selected,
            "requester_answers",
            "brief/requester-answers.json",
            state,
            self.store.artifact_hashes(selected, "brief_draft"),
            "requester",
        )
        return state

    def save_clarification_answer(
        self,
        question_id: str,
        answer: str,
        run_id: str | None = None,
    ) -> dict[str, Any]:
        questions = {row["question_id"]: row for row in self.clarification_questions(run_id)}
        if question_id not in questions:
            raise KeyError(f"Unknown clarification question: {question_id}")
        cleaned = answer.strip()
        if not cleaned:
            raise ValueError("Enter a response before saving")
        state = self.clarification_state(run_id)
        state["answers"][question_id] = cleaned
        skipped = [value for value in state["skipped"] if value != question_id]
        return self._save_clarification_state(state["answers"], skipped, run_id)

    def skip_clarification_question(
        self, question_id: str, run_id: str | None = None
    ) -> dict[str, Any]:
        questions = {row["question_id"]: row for row in self.clarification_questions(run_id)}
        question = questions.get(question_id)
        if not question:
            raise KeyError(f"Unknown clarification question: {question_id}")
        if question["required"]:
            raise ValueError("Required clarification questions cannot be skipped")
        state = self.clarification_state(run_id)
        state["answers"].pop(question_id, None)
        return self._save_clarification_state(
            state["answers"], [*state["skipped"], question_id], run_id
        )

    def clarification_interview(self, run_id: str | None = None):
        from .interview import build_clarification_interview

        return build_clarification_interview(self, self._run_id(run_id))

    def approve(self, answers: dict[str, str], run_id: str | None = None):
        saved = self.clarification_state(run_id)["answers"]
        return self.workflow.approve_brief(self._run_id(run_id), {**saved, **answers})

    def research(
        self,
        *,
        source_urls: list[str] | None = None,
        file_paths: list[str | Path] | None = None,
        run_id: str | None = None,
    ):
        paths = [Path(path) for path in file_paths or []]
        return self.workflow.research(
            self._run_id(run_id), self.credentials, source_urls or [], paths
        )

    def extract(self, run_id: str | None = None):
        return self.workflow.extract(self._run_id(run_id), self.credentials)

    def write_guide(self, run_id: str | None = None) -> str:
        return self.workflow.write_guide(self._run_id(run_id), self.credentials)

    def design(self, run_id: str | None = None):
        return self.workflow.design(self._run_id(run_id), self.credentials)

    def author(self, run_id: str | None = None):
        return self.workflow.author(self._run_id(run_id), self.credentials)

    def preflight(self, run_id: str | None = None):
        return self.workflow.preflight(self._run_id(run_id))

    def plan_visuals(self, run_id: str | None = None):
        return self.workflow.plan_visuals(self._run_id(run_id), self.credentials)

    def generate_images(self, *, confirm_cost: bool = False, run_id: str | None = None):
        selected = self._run_id(run_id)
        manifest = self.store.load_manifest(selected)
        if not manifest.mock and not confirm_cost:
            raise RuntimeError(
                "Image generation is optional and billable. Re-run with confirm_cost=True to proceed."
            )
        return self.workflow.generate_images(selected, self.credentials)

    def source_images(
        self,
        *,
        command: list[str],
        providers: list[str] | None = None,
        judge: str = "openai",
        confirm_generation_fallback: bool = False,
        run_id: str | None = None,
    ):
        """Run the optional ranked Image Source-cery pipeline with provenance."""

        selected_providers = providers or [
            "wikimedia",
            "inaturalist",
            "loc",
            "openverse",
            "nasa",
            "met",
            "unsplash",
            "pexels",
        ]
        if "generate" in selected_providers and not confirm_generation_fallback:
            raise RuntimeError(
                "The provider list includes billable generation. Re-run with "
                "confirm_generation_fallback=True to allow it."
            )
        return self.workflow.source_images(
            self._run_id(run_id),
            self.credentials,
            command=command,
            providers=selected_providers,
            judge=judge,
        )

    def skip_images(self, run_id: str | None = None) -> dict[str, Any]:
        """Create a valid empty ledger so validation can proceed without image generation."""

        selected = self._run_id(run_id)
        manifest = self.store.load_manifest(selected)
        self.store.invalidate_downstream(selected, "image_generation")
        self.store.set_stage(selected, "image_generation", StageState.RUNNING)
        ledger = {"assets": [], "mock": manifest.mock}
        self.store.write_json(
            selected,
            "image_ledger",
            "visuals/image-ledger.json",
            ledger,
            self.store.artifact_hashes(selected, "visual_plan"),
            "requester",
        )
        self.store.set_stage(selected, "image_generation", StageState.COMPLETE)
        return ledger

    def validate(self, run_id: str | None = None):
        return self.workflow.validate(self._run_id(run_id))

    def review(self, run_id: str | None = None):
        return self.workflow.semantic_review(self._run_id(run_id), self.credentials)

    def export(self, run_id: str | None = None) -> Path:
        return self.workflow.export(self._run_id(run_id))

    def diagnostics(
        self,
        destination: str | Path | None = None,
        run_id: str | None = None,
    ) -> Path:
        return build_diagnostics_bundle(self.store, self._run_id(run_id), destination)

    def status(self, run_id: str | None = None) -> dict[str, Any]:
        manifest = self.store.load_manifest(self._run_id(run_id))
        next_stage = next(
            (
                stage
                for stage in STAGES
                if manifest.stages[stage] not in {StageState.COMPLETE, StageState.WAITING_APPROVAL}
            ),
            None,
        )
        return {
            "run_id": manifest.run_id,
            "mode": "mock" if manifest.mock else "live",
            "status": manifest.status,
            "next_stage": next_stage,
            "stages": {name: state.value for name, state in manifest.stages.items()},
            "artifact_count": len(manifest.artifacts),
            "event_count": len(manifest.events),
            "final_bundle_path": manifest.final_bundle_path,
        }

    def status_markdown(self, run_id: str | None = None) -> str:
        selected = self._run_id(run_id)
        manifest = self.store.load_manifest(selected)
        lines = [
            f"### Run `{manifest.run_id}`",
            "",
            f"**Mode:** {'MOCK — cannot publish' if manifest.mock else 'LIVE'}  ",
            f"**Saved at:** `{self.store.root}`  ",
            f"**Artifacts:** {len(manifest.artifacts)} · **Events:** {len(manifest.events)}",
            "",
            "| Stage | State | Agent / model |",
            "|---|---|---|",
        ]
        for stage in STAGES:
            agent, model = self.store._stage_executor(manifest, stage)
            agent = agent or "deterministic"
            actor = agent if not model else f"{agent} / {model}"
            lines.append(
                f"| {_safe_cell(STAGE_NAMES[stage])} | `{manifest.stages[stage].value}` | "
                f"{_safe_cell(actor)} |"
            )
        return "\n".join(lines)

    def activity_markdown(self, limit: int = 25, run_id: str | None = None) -> str:
        manifest = self.store.load_manifest(self._run_id(run_id))
        rows = manifest.events[-limit:]
        lines = [
            "| Time | Stage | State | Activity |",
            "|---|---|---|---|",
        ]
        for event in reversed(rows):
            lines.append(
                f"| {_safe_cell(event.at)} | {_safe_cell(event.stage)} | "
                f"`{event.state.value}` | {_safe_cell(event.message)} |"
            )
        return "\n".join(lines)

    def show_status(self, run_id: str | None = None) -> str:
        markdown = self.status_markdown(run_id)
        try:
            from IPython.display import Markdown, display

            display(Markdown(markdown))
        except ImportError:
            print(markdown)
        return markdown

    def show_activity(self, limit: int = 25, run_id: str | None = None) -> str:
        markdown = self.activity_markdown(limit, run_id)
        try:
            from IPython.display import Markdown, display

            display(Markdown(markdown))
        except ImportError:
            print(markdown)
        return markdown

    def runtime_identity(self) -> dict[str, str | None]:
        return studio_runtime_identity()
