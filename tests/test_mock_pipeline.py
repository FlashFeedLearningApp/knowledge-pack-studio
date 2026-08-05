from __future__ import annotations

import json
import zipfile

import pytest
from jsonschema import Draft202012Validator

from knowledge_pack_studio.diagnostics import build_diagnostics_bundle
from knowledge_pack_studio.models import ClarificationQuestion
from knowledge_pack_studio.notebook import NotebookStudio
from knowledge_pack_studio.schema_loader import load_pack_schema
from knowledge_pack_studio.store import ArtifactStore
from knowledge_pack_studio.ui import _run_snapshot
from knowledge_pack_studio.workflow import StudioWorkflow


def test_mock_pipeline_is_resumable_valid_and_fail_closed(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    workflow = StudioWorkflow(store)

    run_id = workflow.run_all_mock("Create a sample pack")
    manifest = store.load_manifest(run_id)
    report = store.read_json(run_id, "validation/validation-report.json")
    pack = store.read_json(run_id, f"publishable/{manifest.final_pack_id}/pack.json")

    assert manifest.status == "draft_packaged"
    assert manifest.final_bundle_path
    assert report["hard_gates_passed"] is False
    assert report["publishable"] is False
    assert any(issue["code"] == "MOCK_PROVIDER" for issue in report["issues"])
    assert report["metrics"]["evidence_coverage"] == 1.0
    assert report["metrics"]["part_assignment_coverage"] == 1.0
    assert manifest.events
    assert any(
        event.stage == "research" and event.state.value == "running" for event in manifest.events
    )
    assert any(
        event.stage == "export" and event.state.value == "complete" for event in manifest.events
    )

    guide = (store.run_dir(run_id) / "guide/study-guide.md").read_text()
    assert guide.startswith("# How Honey Bees Communicate\n")
    assert "## Reading the dance" in guide
    assert "## How it was decoded" in guide
    assert "## Learning objectives" not in guide
    assert "## Review" not in guide
    assert "[claim-" not in guide

    schema_errors = list(Draft202012Validator(load_pack_schema()).iter_errors(pack))
    assert schema_errors == []


def test_export_contains_publishable_pack_schema_and_audit(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    workflow = StudioWorkflow(store)
    run_id = workflow.run_all_mock()
    manifest = store.load_manifest(run_id)

    with zipfile.ZipFile(manifest.final_bundle_path) as archive:
        names = set(archive.namelist())
        pack_root = f"publishable/{manifest.final_pack_id}"
        assert f"{pack_root}/pack.json" in names
        assert f"{pack_root}/guides/study-guide.md" in names
        assert "audit/schema/pack.schema.json" in names
        assert "audit/schema/pack-design.schema.json" in names
        assert "audit/schema/visual-plan.schema.json" in names
        assert "audit/schema/run-manifest.schema.json" in names
        assert "audit/evidence-ledger.json" in names
        assert "audit/validation-report.json" in names
        assert "README.md" in names
        assert "SHA256SUMS" in names
        assert "DRAFT" in archive.read("README.md").decode("utf-8")


def test_exports_never_contain_secret_values(tmp_path):
    marker = "sk-test-secret-that-must-not-appear"
    store = ArtifactStore(tmp_path / "runs")
    workflow = StudioWorkflow(store)
    run_id = workflow.run_all_mock()
    manifest = store.load_manifest(run_id)

    with zipfile.ZipFile(manifest.final_bundle_path) as archive:
        for name in archive.namelist():
            if name.endswith((".json", ".md", "SHA256SUMS")):
                assert marker not in archive.read(name).decode("utf-8")


def test_manifest_records_hashes_and_no_secret_configuration(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    workflow = StudioWorkflow(store)
    run_id = workflow.run_all_mock()
    manifest = json.loads((store.run_dir(run_id) / "run-manifest.json").read_text())
    config = json.loads((store.run_dir(run_id) / "configuration.json").read_text())

    assert manifest["artifacts"]["pack_json"]["sha256"]
    assert manifest["artifacts"]["evidence_ledger"]["input_hashes"]
    assert "api_key" not in json.dumps(config).lower()


def test_resume_snapshot_restores_the_complete_workspace(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    run_id = StudioWorkflow(store).run_all_mock("Resume this knowledge pack")

    snapshot = _run_snapshot(store, run_id)

    assert snapshot["run_id"] == run_id
    assert snapshot["mock"] is True
    assert snapshot["idea"] == "Resume this knowledge pack"
    assert "Mock research dossier" in snapshot["research_report"]
    assert "# How Honey Bees Communicate" in snapshot["guide_markdown"]
    assert '"target_shape_ratios"' in snapshot["design_json"]
    assert '"items"' in snapshot["items_json"]
    assert snapshot["bundle_file"]
    assert snapshot["selected_tab"] == "validate"
    assert "Deterministic validation needs attention" in snapshot["activity_html"]
    assert snapshot["activity_rows"]


def test_diagnostics_bundle_redacts_keys_and_includes_stage_errors(tmp_path):
    marker = "sk-test-secret-that-must-not-appear"
    store = ArtifactStore(tmp_path / "runs")
    workflow = StudioWorkflow(store)
    run_id = workflow.create_run("Diagnostic test", mock=True)
    store.write_json(
        run_id,
        "test_error",
        "errors/test.json",
        {"message": f"provider rejected {marker}"},
        [],
    )

    target = build_diagnostics_bundle(store, run_id, tmp_path / "downloads")

    with zipfile.ZipFile(target) as archive:
        assert "run/errors/test.json" in archive.namelist()
        combined = "\n".join(
            archive.read(name).decode("utf-8")
            for name in archive.namelist()
            if name.endswith((".json", ".md"))
        )
    assert marker not in combined
    assert "[REDACTED]" in combined


def test_required_clarification_answers_cannot_be_auto_approved(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    workflow = StudioWorkflow(store)
    run_id = workflow.create_run("Approval gate", mock=True)
    draft = workflow.clarify(run_id, {}, {})
    draft.clarification_questions = [
        ClarificationQuestion(
            question_id="scope-boundary",
            question="What is out of scope?",
            why_it_matters="It changes the curriculum boundary.",
        )
    ]
    store.write_json(
        run_id,
        "brief_draft",
        "brief/brief-draft.json",
        draft.model_dump(mode="json"),
        [],
    )

    with pytest.raises(ValueError, match="scope-boundary"):
        workflow.approve_brief(run_id, {})


def test_research_missing_approval_fails_before_the_stage_starts(tmp_path):
    store = ArtifactStore(tmp_path / "runs")
    workflow = StudioWorkflow(store)
    run_id = workflow.create_run("Prerequisite gate", mock=True)
    workflow.clarify(run_id, {}, {})

    with pytest.raises(RuntimeError, match="section 3.*APPROVE_BRIEF"):
        workflow.research(run_id, {})

    manifest = store.load_manifest(run_id)
    assert manifest.stages["research"].value == "not_started"
    assert not (store.run_dir(run_id) / "errors/research.json").exists()


def test_notebook_facade_resumes_artifacts_and_reports_progress(tmp_path):
    first = NotebookStudio(tmp_path / "runs", echo_progress=False)
    run_id = first.workflow.run_all_mock("Notebook resume test")

    resumed = NotebookStudio(tmp_path / "runs", echo_progress=False)
    assert resumed.resume(run_id) == run_id
    status = resumed.status()
    assert status["artifact_count"] > 0
    assert status["event_count"] > 0
    assert status["final_bundle_path"]
    assert "Grounded research" in resumed.status_markdown()


def test_notebook_interview_persists_required_outcome_and_approves(tmp_path):
    studio = NotebookStudio(tmp_path / "runs", echo_progress=False)
    studio.create_run("Interview this idea", mock=True)
    draft = studio.clarify({"audience": "Adult beginners", "desired_outcomes": []})

    question = next(
        row
        for row in draft.clarification_questions
        if row.question_id == "required-learning-outcomes"
    )
    assert question.required is True
    assert question.suggested_answer

    interview = studio.clarification_interview()
    response = interview.children[3]
    save_button = interview.children[4].children[0]
    approve_button = interview.children[5].children[2]
    assert approve_button.disabled is True
    response.value = question.suggested_answer
    save_button.click()
    assert approve_button.disabled is False
    approve_button.click()

    approved = studio.store.read_json(studio.current_run_id, "brief/approved-brief.json")
    assert approved["requester_approved"] is True
    assert approved["requester_answers"][question.question_id] == question.suggested_answer
    assert studio.clarification_state()["answers"][question.question_id]


def test_legacy_brief_is_upgraded_to_require_outcome_confirmation(tmp_path):
    studio = NotebookStudio(tmp_path / "runs", echo_progress=False)
    studio.create_run("Migrate this interview", mock=True)
    studio.clarify(
        {
            "audience": "Adult beginners",
            "desired_outcomes": ["Explain the original requested outcome"],
        }
    )
    intake_path = studio.run_dir / "brief/intake.json"
    intake_path.unlink()

    questions = studio.clarification_questions()
    required = next(row for row in questions if row["question_id"] == "required-learning-outcomes")
    assert required["required"] is True
    assert required["suggested_answer"]
    persisted = studio.store.read_json(studio.current_run_id, "brief/brief-draft.json")
    assert any(
        row["question_id"] == "required-learning-outcomes"
        for row in persisted["clarification_questions"]
    )
