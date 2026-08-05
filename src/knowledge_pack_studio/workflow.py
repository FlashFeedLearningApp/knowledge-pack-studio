"""Deterministic stage orchestration around bounded LLM specialists."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .config import StudioConfig
from .diagnostics import redact_secrets
from .models import (
    ApprovedBrief,
    AuthoredItems,
    BriefDraft,
    EvidenceLedger,
    PackDesign,
    ResearchDossier,
    SemanticReview,
    StageState,
    ValidationReport,
    VisualPlan,
    utc_now,
)
from .pack_builder import build_pack
from .packaging import export_bundle
from .provider import MockProvider, OpenAIProvider, PipelineProvider
from .store import ArtifactStore
from .validation import validate_pack


class StudioWorkflow:
    def __init__(self, store: ArtifactStore | None = None):
        self.store = store or ArtifactStore()

    def create_run(
        self,
        idea: str,
        config: StudioConfig | None = None,
        mock: bool = False,
    ) -> str:
        if not idea.strip():
            raise ValueError("An idea is required")
        manifest = self.store.create_run(idea.strip(), config or StudioConfig(), mock)
        return manifest.run_id

    def _config(self, run_id: str) -> StudioConfig:
        return StudioConfig.model_validate(self.store.read_json(run_id, "configuration.json"))

    def _provider(self, run_id: str, credentials: dict[str, str]) -> PipelineProvider:
        manifest = self.store.load_manifest(run_id)
        config = self._config(run_id)
        if manifest.mock:
            return MockProvider(config)
        return OpenAIProvider(config, credentials)

    def _start(self, run_id: str, stage: str) -> None:
        self.store.invalidate_downstream(run_id, stage)
        self.store.set_stage(run_id, stage, StageState.RUNNING)

    def _fail(self, run_id: str, stage: str, exc: Exception) -> None:
        self.store.write_json(
            run_id,
            f"{stage}_error",
            f"errors/{stage}.json",
            {
                "stage": stage,
                "error": type(exc).__name__,
                "message": redact_secrets(str(exc)),
                "at": utc_now(),
            },
            [],
            "orchestrator",
        )
        self.store.set_stage(run_id, stage, StageState.FAILED)

    def clarify(
        self,
        run_id: str,
        intake: dict[str, Any],
        credentials: dict[str, str],
    ) -> BriefDraft:
        stage = "clarification"
        self._start(run_id, stage)
        try:
            idea = self.store.read_json(run_id, "idea.json")["idea"]
            result, call = self._provider(run_id, credentials).clarify(idea, intake)
            self.store.record_call(run_id, call)
            self.store.write_json(
                run_id,
                "brief_draft",
                "brief/brief-draft.json",
                result.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "idea", "configuration"),
                "clarifier",
            )
            self.store.set_stage(run_id, stage, StageState.WAITING_APPROVAL)
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def approve_brief(self, run_id: str, answers: dict[str, str]) -> ApprovedBrief:
        stage = "brief_approval"
        self._start(run_id, stage)
        try:
            draft = BriefDraft.model_validate(
                self.store.read_json(run_id, "brief/brief-draft.json")
            )
            approved = ApprovedBrief(
                **draft.model_dump(),
                requester_answers=answers,
                requester_approved=True,
                approved_at=utc_now(),
            )
            self.store.write_json(
                run_id,
                "approved_brief",
                "brief/approved-brief.json",
                approved.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "brief_draft"),
                "requester",
            )
            self.store.set_stage(run_id, "clarification", StageState.COMPLETE)
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return approved
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def research(
        self,
        run_id: str,
        credentials: dict[str, str],
        source_urls: list[str] | None = None,
        file_paths: list[Path] | None = None,
    ) -> ResearchDossier:
        stage = "research"
        self._start(run_id, stage)
        try:
            brief = ApprovedBrief.model_validate(
                self.store.read_json(run_id, "brief/approved-brief.json")
            )
            if not brief.requester_approved:
                raise RuntimeError("Research requires an approved brief")
            result, call = self._provider(run_id, credentials).research(
                brief, source_urls or [], file_paths or []
            )
            self.store.record_call(run_id, call)
            self.store.write_json(
                run_id,
                "research_dossier",
                "research/research-dossier.json",
                result.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "approved_brief"),
                "researcher",
            )
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def extract(self, run_id: str, credentials: dict[str, str]) -> EvidenceLedger:
        stage = "extraction"
        self._start(run_id, stage)
        try:
            brief = ApprovedBrief.model_validate(
                self.store.read_json(run_id, "brief/approved-brief.json")
            )
            dossier = ResearchDossier.model_validate(
                self.store.read_json(run_id, "research/research-dossier.json")
            )
            result, call = self._provider(run_id, credentials).extract(brief, dossier)
            self.store.record_call(run_id, call)
            self.store.write_json(
                run_id,
                "evidence_ledger",
                "evidence/evidence-ledger.json",
                result.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "approved_brief", "research_dossier"),
                "extractor",
            )
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def write_guide(self, run_id: str, credentials: dict[str, str]) -> str:
        stage = "study_guide"
        self._start(run_id, stage)
        try:
            brief = ApprovedBrief.model_validate(
                self.store.read_json(run_id, "brief/approved-brief.json")
            )
            ledger = EvidenceLedger.model_validate(
                self.store.read_json(run_id, "evidence/evidence-ledger.json")
            )
            result, call = self._provider(run_id, credentials).write_guide(brief, ledger)
            self.store.record_call(run_id, call)
            self.store.write_text(
                run_id,
                "study_guide",
                "guide/study-guide.md",
                result,
                self.store.artifact_hashes(run_id, "approved_brief", "evidence_ledger"),
                "guide_author",
            )
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def design(self, run_id: str, credentials: dict[str, str]) -> PackDesign:
        stage = "pack_design"
        self._start(run_id, stage)
        try:
            brief = ApprovedBrief.model_validate(
                self.store.read_json(run_id, "brief/approved-brief.json")
            )
            ledger = EvidenceLedger.model_validate(
                self.store.read_json(run_id, "evidence/evidence-ledger.json")
            )
            guide = self.store.read_text(run_id, "guide/study-guide.md")
            result, call = self._provider(run_id, credentials).design(brief, ledger, guide)
            self.store.record_call(run_id, call)
            self.store.write_json(
                run_id,
                "pack_design",
                "design/pack-design.json",
                result.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "evidence_ledger", "study_guide"),
                "pack_designer",
            )
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def author(self, run_id: str, credentials: dict[str, str]) -> AuthoredItems:
        stage = "item_authoring"
        self._start(run_id, stage)
        try:
            brief = ApprovedBrief.model_validate(
                self.store.read_json(run_id, "brief/approved-brief.json")
            )
            ledger = EvidenceLedger.model_validate(
                self.store.read_json(run_id, "evidence/evidence-ledger.json")
            )
            guide = self.store.read_text(run_id, "guide/study-guide.md")
            design = PackDesign.model_validate(
                self.store.read_json(run_id, "design/pack-design.json")
            )
            result, call = self._provider(run_id, credentials).author(brief, ledger, guide, design)
            self.store.record_call(run_id, call)
            self.store.write_json(
                run_id,
                "authored_items",
                "items/authored-items.json",
                result.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "evidence_ledger", "study_guide", "pack_design"),
                "item_author",
            )
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def plan_visuals(self, run_id: str, credentials: dict[str, str]) -> VisualPlan:
        stage = "visual_planning"
        self._start(run_id, stage)
        try:
            ledger = EvidenceLedger.model_validate(
                self.store.read_json(run_id, "evidence/evidence-ledger.json")
            )
            design = PackDesign.model_validate(
                self.store.read_json(run_id, "design/pack-design.json")
            )
            items = AuthoredItems.model_validate(
                self.store.read_json(run_id, "items/authored-items.json")
            )
            result, call = self._provider(run_id, credentials).plan_visuals(ledger, design, items)
            self.store.record_call(run_id, call)
            self.store.write_json(
                run_id,
                "visual_plan",
                "visuals/visual-plan.json",
                result.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "pack_design", "authored_items"),
                "visual_director",
            )
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def generate_images(self, run_id: str, credentials: dict[str, str]) -> dict[str, Any]:
        stage = "image_generation"
        self._start(run_id, stage)
        try:
            manifest = self.store.load_manifest(run_id)
            config = self._config(run_id)
            design = PackDesign.model_validate(
                self.store.read_json(run_id, "design/pack-design.json")
            )
            plan = VisualPlan.model_validate(
                self.store.read_json(run_id, "visuals/visual-plan.json")
            )
            provider = self._provider(run_id, credentials)
            assets: list[dict[str, Any]] = []
            for brief in plan.briefs[: config.image_count_limit]:
                base = {
                    "assetId": brief.asset_id,
                    "itemId": brief.item_id,
                    "kind": brief.kind,
                    "prompt": brief.prompt,
                    "searchTerm": brief.search_term,
                    "altText": brief.alt_text,
                    "model": config.image_model,
                    "generatedAt": utc_now(),
                }
                if manifest.mock or not brief.generate:
                    assets.append(
                        {**base, "status": "skipped", "reason": "Mock or planning-only mode"}
                    )
                    continue
                payload = provider.generate_image(brief.prompt)
                relative = f"publishable/{design.pack_id}/generated/{brief.asset_id}.png"
                record = self.store.write_bytes(
                    run_id,
                    f"image_{brief.asset_id}",
                    relative,
                    payload,
                    self.store.artifact_hashes(run_id, "visual_plan"),
                    "openai_image_generation",
                )
                assets.append(
                    {
                        **base,
                        "status": "generated",
                        "relativePath": f"generated/{brief.asset_id}.png",
                        "sha256": record.sha256,
                        "bytes": len(payload),
                    }
                )
            ledger = {"assets": assets, "mock": manifest.mock}
            self.store.write_json(
                run_id,
                "image_ledger",
                "visuals/image-ledger.json",
                ledger,
                self.store.artifact_hashes(run_id, "visual_plan"),
                "image_generation",
            )
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return ledger
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def _build_consumer_pack(self, run_id: str) -> dict[str, Any]:
        brief = ApprovedBrief.model_validate(
            self.store.read_json(run_id, "brief/approved-brief.json")
        )
        dossier = ResearchDossier.model_validate(
            self.store.read_json(run_id, "research/research-dossier.json")
        )
        ledger = EvidenceLedger.model_validate(
            self.store.read_json(run_id, "evidence/evidence-ledger.json")
        )
        design = PackDesign.model_validate(self.store.read_json(run_id, "design/pack-design.json"))
        authored = AuthoredItems.model_validate(
            self.store.read_json(run_id, "items/authored-items.json")
        )
        image_path = self.store.run_dir(run_id) / "visuals/image-ledger.json"
        image_ledger = json.loads(image_path.read_text()) if image_path.is_file() else None
        pack, item_ledger = build_pack(
            brief,
            design,
            authored,
            ledger,
            [source.model_dump(mode="json") for source in dossier.sources],
            image_ledger,
        )
        pack_root = self.store.run_dir(run_id) / "publishable" / design.pack_id
        guide = self.store.read_text(run_id, "guide/study-guide.md")
        self.store.write_text(
            run_id,
            "publishable_guide",
            f"publishable/{design.pack_id}/guides/study-guide.md",
            guide,
            self.store.artifact_hashes(run_id, "study_guide"),
            "pack_builder",
        )
        self.store.write_json(
            run_id,
            "item_ledger",
            "items/item-ledger.json",
            item_ledger,
            self.store.artifact_hashes(run_id, "authored_items", "evidence_ledger"),
            "pack_builder",
        )
        self.store.write_json(
            run_id,
            "pack_json",
            f"publishable/{design.pack_id}/pack.json",
            pack,
            self.store.artifact_hashes(run_id, "authored_items", "pack_design", "image_ledger"),
            "pack_builder",
        )
        if not pack_root.exists():
            raise RuntimeError("Pack builder did not create the publishable directory")
        return pack

    def validate(self, run_id: str) -> ValidationReport:
        stage = "validation"
        self._start(run_id, stage)
        try:
            pack = self._build_consumer_pack(run_id)
            ledger = EvidenceLedger.model_validate(
                self.store.read_json(run_id, "evidence/evidence-ledger.json")
            )
            design = PackDesign.model_validate(
                self.store.read_json(run_id, "design/pack-design.json")
            )
            authored = AuthoredItems.model_validate(
                self.store.read_json(run_id, "items/authored-items.json")
            )
            manifest = self.store.load_manifest(run_id)
            report = validate_pack(
                pack,
                authored,
                ledger,
                design,
                self.store.run_dir(run_id),
                manifest.schema_version,
                manifest.mock,
            )
            self.store.write_json(
                run_id,
                "validation_report",
                "validation/validation-report.json",
                report.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "pack_json", "item_ledger"),
                "deterministic_validator",
            )
            self.store.set_stage(
                run_id,
                stage,
                StageState.COMPLETE if report.hard_gates_passed else StageState.FAILED,
            )
            return report
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def semantic_review(self, run_id: str, credentials: dict[str, str]) -> SemanticReview:
        stage = "semantic_review"
        self._start(run_id, stage)
        try:
            ledger = EvidenceLedger.model_validate(
                self.store.read_json(run_id, "evidence/evidence-ledger.json")
            )
            design = PackDesign.model_validate(
                self.store.read_json(run_id, "design/pack-design.json")
            )
            items = AuthoredItems.model_validate(
                self.store.read_json(run_id, "items/authored-items.json")
            )
            guide = self.store.read_text(run_id, "guide/study-guide.md")
            result, call = self._provider(run_id, credentials).review(ledger, guide, design, items)
            self.store.record_call(run_id, call)
            self.store.write_json(
                run_id,
                "semantic_review",
                "validation/semantic-review.json",
                result.model_dump(mode="json"),
                self.store.artifact_hashes(run_id, "validation_report", "evidence_ledger"),
                "reviewer",
            )
            report_path = self.store.run_dir(run_id) / "validation/validation-report.json"
            if report_path.is_file():
                report = ValidationReport.model_validate(json.loads(report_path.read_text()))
                report.publishable = report.hard_gates_passed and result.passed
                self.store.write_json(
                    run_id,
                    "validation_report",
                    "validation/validation-report.json",
                    report.model_dump(mode="json"),
                    self.store.artifact_hashes(run_id, "pack_json", "semantic_review"),
                    "release_gate",
                )
            self.store.set_stage(
                run_id, stage, StageState.COMPLETE if result.passed else StageState.FAILED
            )
            return result
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def export(self, run_id: str) -> Path:
        stage = "export"
        self._start(run_id, stage)
        try:
            design = PackDesign.model_validate(
                self.store.read_json(run_id, "design/pack-design.json")
            )
            report = ValidationReport.model_validate(
                self.store.read_json(run_id, "validation/validation-report.json")
            )
            target = export_bundle(self.store.run_dir(run_id), design.pack_id, report.publishable)
            self.store.write_bytes(
                run_id,
                "export_bundle",
                f"exports/{target.name}",
                target.read_bytes(),
                self.store.artifact_hashes(
                    run_id, "pack_json", "validation_report", "semantic_review"
                ),
                "packager",
            )
            manifest = self.store.load_manifest(run_id)
            manifest.final_pack_id = design.pack_id
            manifest.final_bundle_path = str(target)
            manifest.status = "packaged" if report.publishable else "draft_packaged"
            self.store.save_manifest(manifest)
            self.store.set_stage(run_id, stage, StageState.COMPLETE)
            return target
        except Exception as exc:
            self._fail(run_id, stage, exc)
            raise

    def run_all_mock(self, idea: str = "Demonstrate the knowledge-pack pipeline") -> str:
        run_id = self.create_run(idea, mock=True)
        credentials: dict[str, str] = {}
        self.clarify(run_id, {"audience": "Curious adult beginners"}, credentials)
        self.approve_brief(run_id, {})
        self.research(run_id, credentials)
        self.extract(run_id, credentials)
        self.write_guide(run_id, credentials)
        self.design(run_id, credentials)
        self.author(run_id, credentials)
        self.plan_visuals(run_id, credentials)
        self.generate_images(run_id, credentials)
        self.validate(run_id)
        self.semantic_review(run_id, credentials)
        self.export(run_id)
        return run_id
