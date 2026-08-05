"""Colab-friendly Gradio interface with a visual, approval-gated workflow."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .config import StudioConfig
from .diagnostics import build_diagnostics_bundle, redact_secrets
from .models import StageState
from .store import STAGES, ArtifactStore
from .workflow import StudioWorkflow

FLOW_LABELS = {
    "clarification": "Clarify",
    "brief_approval": "Approve",
    "research": "Research",
    "extraction": "Extract",
    "study_guide": "Study guide",
    "pack_design": "Blueprint",
    "item_authoring": "Author",
    "visual_planning": "Visual plan",
    "image_generation": "Images",
    "validation": "Validate",
    "semantic_review": "Review",
    "export": "Export",
}


CSS = """
:root { --kp-bg:#090d18; --kp-panel:#11182a; --kp-line:#2d3850; --kp-text:#edf2ff;
  --kp-muted:#91a0bc; --kp-accent:#8b7cff; --kp-good:#3bd39f; --kp-warn:#ffbe55;
  --kp-bad:#ff6b7a; }
.gradio-container { max-width: 1500px !important; background:var(--kp-bg) !important; }
.kp-hero { padding:26px; border:1px solid #29334a; border-radius:22px;
  background:radial-gradient(circle at 10% 0%,#272350 0,#11182a 43%,#0b101d 100%); }
.kp-hero h1 { margin:0 0 8px; color:var(--kp-text); font-size:34px; }
.kp-hero p { margin:0; color:#aeb9cf; max-width:880px; }
.kp-flow { display:grid; grid-template-columns:repeat(6,minmax(0,1fr)); gap:12px;
  padding:18px 4px 24px; }
.kp-node { position:relative; min-width:0; padding:12px 10px; border-radius:14px;
  border:1px solid #303a52; background:#12192a; color:#eaf0ff; text-align:center;
  font-size:12px; font-weight:700; }
.kp-node:not(:nth-child(6n))::after { content:"→"; position:absolute; right:-11px;
  top:50%; transform:translate(50%,-50%); color:var(--kp-line); font-size:15px; }
.kp-node small { display:block; margin-top:5px; color:#8d9ab4; font-weight:500; }
.kp-node.complete { border-color:#2c9b79; box-shadow:0 0 0 1px #2c9b7944 inset; }
.kp-node.complete small { color:var(--kp-good); }
.kp-node.running { border-color:#7368ff; box-shadow:0 0 22px #7368ff33; }
.kp-node.running small { color:#a9a1ff; }
.kp-node.waiting_approval { border-color:#a87925; }
.kp-node.waiting_approval small { color:var(--kp-warn); }
.kp-node.failed { border-color:#b54a58; }
.kp-node.failed small { color:var(--kp-bad); }
.kp-node.stale { border-style:dashed; border-color:#7a718d; }
.kp-note { color:#aab6cc; font-size:13px; }
.kp-warning { padding:12px 14px; border-radius:12px; border:1px solid #665327;
  background:#2a2111; color:#ffd98b; }
.kp-mode { margin:14px 0; padding:14px 16px; border-radius:14px; font-weight:700; }
.kp-mode strong { display:block; margin-bottom:3px; font-size:16px; }
.kp-mode.mock { color:#ffe09b; background:#30220e; border:2px solid #c98a28;
  box-shadow:0 0 20px #c98a2822; }
.kp-mode.live { color:#a9f0d6; background:#102a23; border:2px solid #2c9b79; }
.kp-status { padding:10px 14px; border-left:3px solid var(--kp-accent); background:#11182a; }
.kp-next { margin-top:20px; padding-top:16px; border-top:1px solid #2d3850; }
.kp-next p { margin:0; color:var(--kp-muted); font-size:13px; }
@media (max-width:900px) {
  .kp-flow { grid-template-columns:repeat(3,minmax(0,1fr)); }
  .kp-node:nth-child(3n)::after { content:none; }
}
"""


def _flow_html(store: ArtifactStore, run_id: str | None) -> str:
    stages = {name: StageState.NOT_STARTED for name in STAGES}
    if run_id:
        try:
            stages = store.load_manifest(run_id).stages
        except Exception:
            pass
    nodes: list[str] = []
    for stage in STAGES:
        state = stages[stage]
        nodes.append(
            f'<div class="kp-node {state.value}">{FLOW_LABELS[stage]}'
            f"<small>{state.value.replace('_', ' ')}</small></div>"
        )
    return '<div class="kp-flow">' + "".join(nodes) + "</div>"


def _json(value: Any) -> str:
    if hasattr(value, "model_dump"):
        value = value.model_dump(mode="json")
    return json.dumps(value, indent=2, ensure_ascii=False)


def _require_run(run_id: str) -> str:
    if not run_id:
        raise ValueError("Create or load a run first")
    return run_id


def _file_paths(files: Any) -> list[Path]:
    if not files:
        return []
    values = files if isinstance(files, list) else [files]
    result: list[Path] = []
    for value in values:
        candidate = getattr(value, "name", value)
        result.append(Path(str(candidate)))
    return result


def _lines(value: str | None) -> list[str]:
    return [line.strip() for line in (value or "").splitlines() if line.strip()]


def _in_colab() -> bool:
    return "COLAB_RELEASE_TAG" in os.environ or Path("/content").is_dir()


def _validate_share_auth(share: bool, auth: Any) -> None:
    """Refuse an unauthenticated public tunnel, which would expose callbacks and run data."""

    if share and not auth:
        raise RuntimeError(
            "Public Gradio share links require authentication. Pass auth=(username, password) "
            "or launch locally with share=False."
        )


def _mode_html(mock: bool) -> str:
    if mock:
        return (
            '<div class="kp-mode mock"><strong>MOCK DEMONSTRATION MODE</strong>'
            "Uses simulated research and content. No OpenAI charges, but this run can never pass "
            "the publication gate.</div>"
        )
    return (
        '<div class="kp-mode live"><strong>LIVE OPENAI MODE</strong>'
        "Uses the connected API key for research and generation. Provider usage may incur "
        "charges.</div>"
    )


def _credential_markdown(connected: bool) -> str:
    if connected:
        return (
            "✅ **OpenAI credential connected** from `OPENAI_API_KEY_FF_KP`. "
            "The key is not exposed to the browser or Gradio callbacks."
        )
    return (
        "⚠️ **No OpenAI credential connected.** Mock mode works normally; live mode requires "
        "the Colab Secret or local environment variable `OPENAI_API_KEY_FF_KP`, followed by a "
        "runtime restart."
    )


def _questions_markdown(brief: dict[str, Any] | None) -> str:
    if not brief:
        return ""
    questions = brief.get("clarification_questions", [])
    return (
        "\n".join(
            f"- **{row['question_id']}:** {row['question']}  \n  _{row['why_it_matters']}_"
            for row in questions
        )
        or "No material clarification questions were identified. Review and explicitly approve the brief."
    )


def _source_rows(dossier: dict[str, Any] | None) -> list[list[str]]:
    if not dossier:
        return []
    return [
        [
            source.get("source_id", ""),
            source.get("title", ""),
            source.get("author_or_institution", ""),
            source.get("publication_date") or "",
            source.get("source_type", ""),
            source.get("url", ""),
        ]
        for source in dossier.get("sources", [])
    ]


def _selected_tab(stages: dict[str, StageState]) -> str:
    groups = (
        ("idea", ("clarification", "brief_approval")),
        ("research", ("research", "extraction")),
        ("guide", ("study_guide", "pack_design")),
        ("author", ("item_authoring", "visual_planning")),
        ("validate", ("validation", "semantic_review", "export")),
    )
    for tab_id, names in groups:
        if any(stages[name] != StageState.COMPLETE for name in names):
            return tab_id
    return "validate"


def _stage_status(stages: dict[str, StageState], stage: str, ready: str, complete: str) -> str:
    state = stages[stage]
    if state == StageState.COMPLETE:
        return f"✅ {complete}"
    if state == StageState.FAILED:
        return "❌ The previous attempt failed. Retry this step or download session diagnostics."
    if state == StageState.RUNNING:
        return "⚠️ The previous attempt did not finish. It is safe to retry this step."
    if state == StageState.STALE:
        return "⚠️ An upstream artifact changed. Run this step again."
    return ready


def _read_json_if_present(store: ArtifactStore, run_id: str, path: str) -> Any:
    target = store.run_dir(run_id) / path
    return store.read_json(run_id, path) if target.is_file() else None


def _read_text_if_present(store: ArtifactStore, run_id: str, path: str) -> str:
    target = store.run_dir(run_id) / path
    return store.read_text(run_id, path) if target.is_file() else ""


def _run_snapshot(store: ArtifactStore, run_id: str) -> dict[str, Any]:
    """Load every persisted UI artifact so Resume restores the authoring workspace."""

    manifest = store.load_manifest(run_id)
    idea_record = store.read_json(run_id, "idea.json")
    config = store.read_json(run_id, "configuration.json")
    draft = _read_json_if_present(store, run_id, "brief/brief-draft.json")
    approved = _read_json_if_present(store, run_id, "brief/approved-brief.json")
    dossier = _read_json_if_present(store, run_id, "research/research-dossier.json")
    evidence = _read_json_if_present(store, run_id, "evidence/evidence-ledger.json")
    design = _read_json_if_present(store, run_id, "design/pack-design.json")
    items = _read_json_if_present(store, run_id, "items/authored-items.json")
    visual = _read_json_if_present(store, run_id, "visuals/visual-plan.json")
    images = _read_json_if_present(store, run_id, "visuals/image-ledger.json")
    validation = _read_json_if_present(store, run_id, "validation/validation-report.json")
    review = _read_json_if_present(store, run_id, "validation/semantic-review.json")
    bundle_path = None
    if "export_bundle" in manifest.artifacts:
        candidate = store.artifact_path(run_id, "export_bundle")
        bundle_path = str(candidate) if candidate.is_file() else None
    restored = sum(
        value not in (None, "", [], {})
        for value in (
            draft,
            approved,
            dossier,
            evidence,
            design,
            items,
            visual,
            images,
            validation,
            review,
        )
    )
    selected_tab = _selected_tab(manifest.stages)
    return {
        "run_id": run_id,
        "flow": _flow_html(store, run_id),
        "mode_html": _mode_html(manifest.mock),
        "mock": manifest.mock,
        "config_json": json.dumps(config, indent=2, ensure_ascii=False),
        "idea": idea_record.get("idea", ""),
        "brief_draft": _json(draft) if draft else "",
        "questions": _questions_markdown(draft),
        "answers": _json((approved or {}).get("requester_answers", {})),
        "approved_brief": _json(approved) if approved else "",
        "source_urls": "\n".join(
            source.get("url", "") for source in (dossier or {}).get("sources", [])
        ),
        "research_report": (dossier or {}).get("report_markdown", ""),
        "source_table": _source_rows(dossier),
        "evidence_json": _json(evidence) if evidence else "",
        "guide_status": _stage_status(
            manifest.stages,
            "study_guide",
            "Ready to write the learner-facing study guide.",
            "Study guide complete.",
        ),
        "guide_markdown": _read_text_if_present(store, run_id, "guide/study-guide.md"),
        "design_status": _stage_status(
            manifest.stages,
            "pack_design",
            "Create the guide before building its lesson and item blueprint.",
            "Lesson and item blueprint complete.",
        ),
        "design_json": _json(design) if design else "",
        "author_status": _stage_status(
            manifest.stages,
            "item_authoring",
            "Create the blueprint before authoring seed items.",
            "Seed-item authoring complete.",
        ),
        "items_json": _json(items) if items else "",
        "visual_json": _json(visual) if visual else "",
        "image_json": _json(images) if images else "",
        "validation_json": _json(validation) if validation else "",
        "review_json": _json(review) if review else "",
        "bundle_file": bundle_path,
        "selected_tab": selected_tab,
        "load_status": (
            f"✅ Restored run `{run_id}` with {restored} persisted stage artifacts. "
            "Uploaded source files cannot be reattached automatically."
        ),
    }


def build_app(run_root: str | Path | None = None, default_api_key: str | None = None):
    try:
        import gradio as gr
    except ImportError as exc:
        raise RuntimeError("Install project dependencies to launch the Studio UI") from exc

    store = ArtifactStore(run_root)
    workflow = StudioWorkflow(store)
    default_config = StudioConfig().model_dump_json(indent=2)
    guide_progress = gr.Progress()
    design_progress = gr.Progress()
    author_progress = gr.Progress()
    lucky_progress = gr.Progress()

    def credentials() -> dict[str, str]:
        key = (default_api_key or "").strip()
        return {"default": key} if key else {}

    def create_and_clarify(
        idea: str,
        audience: str,
        outcomes: str,
        constraints: str,
        config_json: str,
        mock: bool,
    ):
        config = StudioConfig.model_validate_json(config_json)
        run_id = workflow.create_run(idea, config=config, mock=mock)
        intake = {
            "audience": audience,
            "desired_outcomes": _lines(outcomes),
            "constraints": _lines(constraints),
        }
        brief = workflow.clarify(run_id, intake, credentials())
        questions = _questions_markdown(brief.model_dump(mode="json"))
        return (
            run_id,
            gr.Dropdown(choices=store.list_runs(), value=run_id),
            _json(brief),
            questions,
            _flow_html(store, run_id),
        )

    def approve(run_id: str, answers_json: str):
        run_id = _require_run(run_id)
        answers = json.loads(answers_json or "{}")
        brief = workflow.approve_brief(run_id, answers)
        return _json(brief), _flow_html(store, run_id)

    def run_research(run_id: str, source_urls: str, files: Any):
        run_id = _require_run(run_id)
        urls = _lines(source_urls)
        dossier = workflow.research(run_id, credentials(), urls, _file_paths(files))
        source_table = [
            [
                source.source_id,
                source.title,
                source.author_or_institution,
                source.publication_date or "",
                source.source_type,
                source.url,
            ]
            for source in dossier.sources
        ]
        return dossier.report_markdown, source_table, _flow_html(store, run_id)

    def run_extraction(run_id: str):
        run_id = _require_run(run_id)
        ledger = workflow.extract(run_id, credentials())
        return _json(ledger), _flow_html(store, run_id)

    def run_guide(run_id: str, progress=guide_progress):
        run_id = _require_run(run_id)
        progress(0.1, desc="Preparing the approved evidence…")
        try:
            guide = workflow.write_guide(run_id, credentials())
            progress(1.0, desc="Study guide complete")
            return guide, "✅ Study guide complete.", _flow_html(store, run_id)
        except Exception as exc:
            gr.Warning("Study-guide generation failed. You can retry or download diagnostics.")
            return (
                gr.skip(),
                f"❌ Study-guide generation failed: `{type(exc).__name__}`. "
                "Retry this step or download session diagnostics below.",
                _flow_html(store, run_id),
            )

    def run_design(run_id: str, progress=design_progress):
        run_id = _require_run(run_id)
        progress(0.1, desc="Mapping guide sections to pack parts…")
        try:
            design = workflow.design(run_id, credentials())
            progress(1.0, desc="Lesson and item blueprint complete")
            return (
                _json(design),
                "✅ Lesson and item blueprint complete.",
                _flow_html(store, run_id),
            )
        except Exception as exc:
            gr.Warning("Blueprint generation failed. You can retry or download diagnostics.")
            return (
                gr.skip(),
                f"❌ Blueprint generation failed: `{type(exc).__name__}`. "
                "Retry this step or download session diagnostics below.",
                _flow_html(store, run_id),
            )

    def run_author(run_id: str, progress=author_progress):
        run_id = _require_run(run_id)
        progress(0.1, desc="Drafting evidence-linked seed items…")
        try:
            items = workflow.author(run_id, credentials())
            progress(1.0, desc="Seed items complete")
            return (
                _json(items),
                "✅ Seed-item authoring complete.",
                _flow_html(store, run_id),
            )
        except Exception as exc:
            gr.Warning("Seed-item authoring failed. You can retry or download diagnostics.")
            return (
                gr.skip(),
                f"❌ Seed-item authoring failed: `{type(exc).__name__}`. "
                "Retry this step or download session diagnostics below.",
                _flow_html(store, run_id),
            )

    def run_visual_plan(run_id: str):
        run_id = _require_run(run_id)
        plan = workflow.plan_visuals(run_id, credentials())
        return _json(plan), _flow_html(store, run_id)

    def run_images(run_id: str):
        run_id = _require_run(run_id)
        ledger = workflow.generate_images(run_id, credentials())
        return _json(ledger), _flow_html(store, run_id)

    def run_validation(run_id: str):
        run_id = _require_run(run_id)
        report = workflow.validate(run_id)
        return _json(report), _flow_html(store, run_id)

    def run_review(run_id: str):
        run_id = _require_run(run_id)
        review = workflow.semantic_review(run_id, credentials())
        report = store.read_json(run_id, "validation/validation-report.json")
        return _json(review), _json(report), _flow_html(store, run_id)

    def run_export(run_id: str):
        run_id = _require_run(run_id)
        target = workflow.export(run_id)
        download_dir = Path(tempfile.mkdtemp(prefix="knowledge-pack-studio-"))
        download_target = download_dir / target.name
        shutil.copy2(target, download_target)
        return str(download_target), _flow_html(store, run_id)

    def snapshot_values(snapshot: dict[str, Any]):
        bundle_file = snapshot["bundle_file"]
        if bundle_file:
            download_dir = Path(tempfile.mkdtemp(prefix="knowledge-pack-studio-resume-"))
            copied_bundle = download_dir / Path(bundle_file).name
            shutil.copy2(bundle_file, copied_bundle)
            bundle_file = str(copied_bundle)
        return (
            snapshot["run_id"],
            gr.Dropdown(choices=store.list_runs(), value=snapshot["run_id"]),
            snapshot["flow"],
            snapshot["mode_html"],
            snapshot["mock"],
            snapshot["config_json"],
            snapshot["idea"],
            snapshot["brief_draft"],
            snapshot["questions"],
            snapshot["answers"],
            snapshot["approved_brief"],
            snapshot["source_urls"],
            snapshot["research_report"],
            snapshot["source_table"],
            snapshot["evidence_json"],
            snapshot["guide_status"],
            snapshot["guide_markdown"],
            snapshot["design_status"],
            snapshot["design_json"],
            snapshot["author_status"],
            snapshot["items_json"],
            snapshot["visual_json"],
            snapshot["image_json"],
            snapshot["validation_json"],
            snapshot["review_json"],
            bundle_file,
            gr.Tabs(selected=snapshot["selected_tab"]),
            snapshot["load_status"],
        )

    def load_run(selected: str):
        return snapshot_values(_run_snapshot(store, _require_run(selected or "")))

    lucky_groups = (
        "Research and extract evidence",
        "Write guide and create lesson/item blueprint",
        "Author seed items and plan visuals",
        "Generate planned images",
        "Validate and run semantic review",
        "Build the export bundle",
    )

    def run_lucky(
        idea: str,
        audience: str,
        outcomes: str,
        constraints: str,
        config_json: str,
        mock: bool,
        source_urls: str,
        files: Any,
        auto_approve: bool,
        selected_groups: list[str],
        progress=lucky_progress,
    ):
        config = StudioConfig.model_validate_json(config_json)
        run_id = workflow.create_run(idea, config=config, mock=mock)
        intake = {
            "audience": audience,
            "desired_outcomes": _lines(outcomes),
            "constraints": _lines(constraints),
        }
        try:
            progress(0.05, desc="Clarifying the idea…")
            workflow.clarify(run_id, intake, credentials())
            if not auto_approve:
                snapshot = _run_snapshot(store, run_id)
                snapshot["load_status"] = (
                    "⚠️ Automation stopped at brief approval. Review the draft, approve it, then "
                    "continue through the guided steps."
                )
                return snapshot_values(snapshot)

            workflow.approve_brief(run_id, {})
            chosen = set(selected_groups or [])
            wants_export = lucky_groups[5] in chosen
            wants_review = lucky_groups[4] in chosen or wants_export
            wants_images = lucky_groups[3] in chosen
            wants_author = lucky_groups[2] in chosen or wants_images or wants_review
            wants_guide = lucky_groups[1] in chosen or wants_author
            wants_research = lucky_groups[0] in chosen or wants_guide

            if wants_research:
                progress(0.15, desc="Researching and extracting evidence…")
                urls = _lines(source_urls)
                workflow.research(run_id, credentials(), urls, _file_paths(files))
                workflow.extract(run_id, credentials())
            if wants_guide:
                progress(0.4, desc="Writing the guide and blueprint…")
                workflow.write_guide(run_id, credentials())
                workflow.design(run_id, credentials())
            if wants_author:
                progress(0.6, desc="Authoring items and planning visuals…")
                workflow.author(run_id, credentials())
                workflow.plan_visuals(run_id, credentials())
            if wants_images:
                progress(0.75, desc="Generating planned images…")
                workflow.generate_images(run_id, credentials())
            if wants_review:
                progress(0.85, desc="Validating and reviewing…")
                workflow.validate(run_id)
                workflow.semantic_review(run_id, credentials())
            if wants_export:
                progress(0.95, desc="Building the export bundle…")
                workflow.export(run_id)
            progress(1.0, desc="Selected automation complete")
            snapshot = _run_snapshot(store, run_id)
            snapshot["load_status"] = (
                "✅ Automatic execution finished. Review every artifact and any failed "
                "publication gates."
            )
            return snapshot_values(snapshot)
        except Exception as exc:
            store.write_json(
                run_id,
                "automation_error",
                "errors/automation.json",
                {
                    "stage": "automatic_pipeline",
                    "error": type(exc).__name__,
                    "message": redact_secrets(str(exc)),
                },
                [],
                "gradio_automation",
            )
            snapshot = _run_snapshot(store, run_id)
            snapshot["load_status"] = (
                f"❌ Automation stopped after `{type(exc).__name__}`. Completed artifacts were "
                "restored; retry the failed step or download diagnostics."
            )
            gr.Warning("Automatic run stopped. Completed artifacts were preserved.")
            return snapshot_values(snapshot)

    def download_diagnostics(run_id: str):
        run_id = _require_run(run_id)
        target = build_diagnostics_bundle(store, run_id)
        return str(target), f"✅ Diagnostics prepared for `{run_id}`. Review before sharing."

    with gr.Blocks(title="Knowledge Pack Studio") as app:
        gr.HTML(
            """<div class="kp-hero"><h1>Knowledge Pack Studio</h1>
            <p>Turn an idea into an evidence-led FlashFeed pack through explicit research,
            extraction, study, design, authoring, visual, and validation stages.</p></div>"""
        )
        gr.HTML(
            """<div class="kp-warning"><strong>Credential policy:</strong> keys are passed to the
            current Colab/Python process only. They are not written into run artifacts or exports.
            Public Colab launches also require password authentication. Mock mode requires no key
            and can never pass the publication gate.</div>"""
        )
        mode_banner = gr.HTML(_mode_html(True))
        flow = gr.HTML(_flow_html(store, None))
        load_status = gr.Markdown(
            "Start a new run or restore a previous run. Resume reloads every persisted artifact.",
            elem_classes="kp-status",
        )
        with gr.Row():
            run_id = gr.Textbox(label="Current run ID", interactive=False, scale=3)
            recent = gr.Dropdown(
                choices=store.list_runs(), label="Resume a run", allow_custom_value=False, scale=2
            )
            load_button = gr.Button("Load", scale=1)
        with gr.Accordion("Provider and model settings — verify before starting", open=True):
            with gr.Row():
                gr.Markdown(_credential_markdown(bool(default_api_key)), elem_classes="kp-status")
                mock_mode = gr.Checkbox(
                    label="MOCK demonstration mode — simulated output; cannot publish", value=True
                )
            with gr.Accordion("Advanced model and run configuration", open=False):
                config_json = gr.Code(
                    value=default_config,
                    language="json",
                    label="Versioned run configuration",
                )

        with gr.Tabs(selected="idea") as main_tabs:
            with gr.Tab("1 · Idea and brief", id="idea"):
                idea = gr.Textbox(
                    label="Idea",
                    lines=4,
                    placeholder="What should someone understand or be able to do?",
                )
                with gr.Row():
                    audience = gr.Textbox(label="Audience", value="Curious adult beginners")
                    outcomes = gr.Textbox(label="Desired outcomes (one per line)", lines=3)
                    constraints = gr.Textbox(label="Constraints (one per line)", lines=3)
                with gr.Accordion("🍀 I'm Feeling Lucky — run selected stages automatically"):
                    gr.Markdown(
                        "Select how far the new run should go. Later stages automatically run "
                        "their required earlier stages; image generation remains separately "
                        "optional. Live mode can incur API charges."
                    )
                    lucky_auto_approve = gr.Checkbox(
                        label=(
                            "Auto-approve the drafted brief without human review "
                            "(required to continue past clarification)"
                        ),
                        value=False,
                    )
                    lucky_stages = gr.CheckboxGroup(
                        choices=list(lucky_groups),
                        value=[
                            lucky_groups[0],
                            lucky_groups[1],
                            lucky_groups[2],
                            lucky_groups[4],
                            lucky_groups[5],
                        ],
                        label="Automatic stage groups",
                    )
                    lucky_button = gr.Button("Run selected automatic pipeline", variant="secondary")
                create_button = gr.Button("Create run and draft brief", variant="primary")
                brief_draft = gr.Code(label="Draft brief", language="json")
                questions = gr.Markdown()
                answers = gr.Code(
                    value="{}",
                    language="json",
                    label='Answers keyed by question ID, for example {"audience-depth": "..."}',
                )
                approve_button = gr.Button("Approve brief")
                approved_brief = gr.Code(label="Approved brief", language="json")
                with gr.Row(elem_classes="kp-next"):
                    gr.Markdown("Brief approved? Continue to the next high-level step.")
                    next_research = gr.Button("Next: Research and extraction →", variant="primary")

            with gr.Tab("2 · Research and extraction", id="research"):
                source_urls = gr.Textbox(label="Requester source URLs (one per line)", lines=4)
                uploads = gr.File(label="Requester files", file_count="multiple", type="filepath")
                research_button = gr.Button("Run grounded research", variant="primary")
                research_report = gr.Markdown()
                source_table = gr.Dataframe(
                    headers=["ID", "Title", "Institution", "Published", "Type", "URL"],
                    datatype=["str", "str", "str", "str", "str", "str"],
                    label="Sources",
                    interactive=False,
                )
                extraction_button = gr.Button("Extract evidence ledger")
                evidence_json = gr.Code(label="Evidence ledger", language="json")
                with gr.Row(elem_classes="kp-next"):
                    gr.Markdown("Evidence extracted? Continue to the learner-facing guide.")
                    next_guide = gr.Button("Next: Study guide and blueprint →", variant="primary")

            with gr.Tab("3 · Study guide and blueprint", id="guide"):
                gr.Markdown("### Learner-facing study guide")
                gr.Markdown(
                    "Writes the lesson prose readers will see, using only approved evidence."
                )
                guide_button = gr.Button("Write learner-facing study guide", variant="primary")
                guide_status = gr.Markdown(
                    "Ready to write the learner-facing study guide.", elem_classes="kp-status"
                )
                guide_markdown = gr.Markdown()
                gr.Markdown("### Lesson and item blueprint")
                gr.Markdown(
                    "Maps guide sections to lesson parts, approved claims, planned item types, "
                    "and target item ratios. It plans the pack; the next page authors the items."
                )
                design_button = gr.Button("Create lesson and item blueprint")
                design_status = gr.Markdown(
                    "Create the guide before building its lesson and item blueprint.",
                    elem_classes="kp-status",
                )
                design_json = gr.Code(label="Lesson and item blueprint (JSON)", language="json")
                with gr.Row(elem_classes="kp-next"):
                    gr.Markdown("Guide and design ready? Continue to item and visual authoring.")
                    next_author = gr.Button("Next: Author and visuals →", variant="primary")

            with gr.Tab("4 · Author and visuals", id="author"):
                author_button = gr.Button("Author seed items", variant="primary")
                author_status = gr.Markdown(
                    "Create the blueprint before authoring seed items.", elem_classes="kp-status"
                )
                items_json = gr.Code(label="Authored items", language="json")
                visual_button = gr.Button("Plan instructional visuals")
                visual_json = gr.Code(label="Visual plan", language="json")
                image_button = gr.Button("Generate approved images")
                image_json = gr.Code(label="Image ledger", language="json")
                with gr.Row(elem_classes="kp-next"):
                    gr.Markdown("Content and visuals ready? Continue to the quality gates.")
                    next_validate = gr.Button(
                        "Next: Validate, review, and export →", variant="primary"
                    )

            with gr.Tab("5 · Validate, review, and export", id="validate"):
                validate_button = gr.Button("Run deterministic validation", variant="primary")
                validation_json = gr.Code(label="Validation report", language="json")
                review_button = gr.Button("Run independent semantic review")
                review_json = gr.Code(label="Semantic review", language="json")
                export_button = gr.Button("Build portable bundle")
                bundle_file = gr.File(label="Knowledge-pack bundle")

        with gr.Group():
            gr.Markdown("### Support and session diagnostics")
            gr.Markdown(
                "Download reproducibility metadata, stage errors, and textual run artifacts. "
                "Credentials are not persisted and key patterns are redacted, but the bundle may "
                "contain your topic, research, and source URLs."
            )
            diagnostics_button = gr.Button("Download session diagnostics")
            diagnostics_status = gr.Markdown()
            diagnostics_file = gr.File(label="Session diagnostics")

        create_button.click(
            create_and_clarify,
            [idea, audience, outcomes, constraints, config_json, mock_mode],
            [run_id, recent, brief_draft, questions, flow],
        )
        approve_button.click(approve, [run_id, answers], [approved_brief, flow])
        research_button.click(
            run_research,
            [run_id, source_urls, uploads],
            [research_report, source_table, flow],
        )
        extraction_button.click(run_extraction, [run_id], [evidence_json, flow])
        guide_start = guide_button.click(
            lambda: "⏳ Writing the learner-facing study guide…",
            outputs=guide_status,
            queue=False,
        )
        guide_start.then(
            run_guide,
            [run_id],
            [guide_markdown, guide_status, flow],
            show_progress="full",
            show_progress_on=guide_status,
        )
        design_start = design_button.click(
            lambda: "⏳ Mapping lesson parts, claims, item types, and target ratios…",
            outputs=design_status,
            queue=False,
        )
        design_start.then(
            run_design,
            [run_id],
            [design_json, design_status, flow],
            show_progress="full",
            show_progress_on=design_status,
        )
        author_start = author_button.click(
            lambda: "⏳ Drafting evidence-linked seed items…",
            outputs=author_status,
            queue=False,
        )
        author_start.then(
            run_author,
            [run_id],
            [items_json, author_status, flow],
            show_progress="full",
            show_progress_on=author_status,
        )
        visual_button.click(run_visual_plan, [run_id], [visual_json, flow])
        image_button.click(run_images, [run_id], [image_json, flow])
        validate_button.click(run_validation, [run_id], [validation_json, flow])
        review_button.click(
            run_review,
            [run_id],
            [review_json, validation_json, flow],
        )
        export_button.click(run_export, [run_id], [bundle_file, flow])
        resume_outputs = [
            run_id,
            recent,
            flow,
            mode_banner,
            mock_mode,
            config_json,
            idea,
            brief_draft,
            questions,
            answers,
            approved_brief,
            source_urls,
            research_report,
            source_table,
            evidence_json,
            guide_status,
            guide_markdown,
            design_status,
            design_json,
            author_status,
            items_json,
            visual_json,
            image_json,
            validation_json,
            review_json,
            bundle_file,
            main_tabs,
            load_status,
        ]
        load_button.click(load_run, [recent], resume_outputs)
        lucky_button.click(
            run_lucky,
            [
                idea,
                audience,
                outcomes,
                constraints,
                config_json,
                mock_mode,
                source_urls,
                uploads,
                lucky_auto_approve,
                lucky_stages,
            ],
            resume_outputs,
            show_progress="full",
            show_progress_on=load_status,
        )
        mock_mode.change(lambda selected: _mode_html(selected), mock_mode, mode_banner)
        diagnostics_button.click(
            download_diagnostics,
            [run_id],
            [diagnostics_file, diagnostics_status],
        )
        next_research.click(lambda: gr.Tabs(selected="research"), outputs=main_tabs)
        next_guide.click(lambda: gr.Tabs(selected="guide"), outputs=main_tabs)
        next_author.click(lambda: gr.Tabs(selected="author"), outputs=main_tabs)
        next_validate.click(lambda: gr.Tabs(selected="validate"), outputs=main_tabs)

    return app


def launch(
    api_key: str | None = None,
    run_root: str | Path | None = None,
    share: bool | None = None,
    **launch_kwargs: Any,
):
    """Launch inline in Colab or locally; the key is intentionally not persisted."""

    import gradio as gr

    if share is None:
        share = _in_colab()
    _validate_share_auth(share, launch_kwargs.get("auth"))
    app = build_app(run_root, default_api_key=api_key)
    return app.launch(
        share=share,
        inline=True,
        show_error=True,
        css=CSS,
        theme=gr.themes.Base(),
        **launch_kwargs,
    )
