"""Colab-friendly Gradio interface with a visual, approval-gated workflow."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Any

from .config import StudioConfig
from .models import StageState
from .store import STAGES, ArtifactStore
from .workflow import StudioWorkflow

FLOW_LABELS = {
    "clarification": "Clarify",
    "brief_approval": "Approve",
    "research": "Research",
    "extraction": "Extract",
    "study_guide": "Study guide",
    "pack_design": "Design",
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


def _in_colab() -> bool:
    return "COLAB_RELEASE_TAG" in os.environ or Path("/content").is_dir()


def build_app(run_root: str | Path | None = None, default_api_key: str | None = None):
    try:
        import gradio as gr
    except ImportError as exc:
        raise RuntimeError("Install project dependencies to launch the Studio UI") from exc

    store = ArtifactStore(run_root)
    workflow = StudioWorkflow(store)
    default_config = StudioConfig().model_dump_json(indent=2)

    def credentials(entered_key: str) -> dict[str, str]:
        key = (entered_key or default_api_key or "").strip()
        return {"default": key} if key else {}

    def create_and_clarify(
        idea: str,
        audience: str,
        outcomes: str,
        constraints: str,
        config_json: str,
        mock: bool,
        api_key: str,
    ):
        config = StudioConfig.model_validate_json(config_json)
        run_id = workflow.create_run(idea, config=config, mock=mock)
        intake = {
            "audience": audience,
            "desired_outcomes": [line.strip() for line in outcomes.splitlines() if line.strip()],
            "constraints": [line.strip() for line in constraints.splitlines() if line.strip()],
        }
        brief = workflow.clarify(run_id, intake, credentials(api_key))
        questions = (
            "\n".join(
                f"- **{question.question_id}:** {question.question}  \n  _{question.why_it_matters}_"
                for question in brief.clarification_questions
            )
            or "No material clarification questions were identified. Review and explicitly approve the brief."
        )
        return run_id, _json(brief), questions, _flow_html(store, run_id)

    def approve(run_id: str, answers_json: str):
        run_id = _require_run(run_id)
        answers = json.loads(answers_json or "{}")
        brief = workflow.approve_brief(run_id, answers)
        return _json(brief), _flow_html(store, run_id)

    def run_research(run_id: str, api_key: str, source_urls: str, files: Any):
        run_id = _require_run(run_id)
        urls = [line.strip() for line in source_urls.splitlines() if line.strip()]
        dossier = workflow.research(run_id, credentials(api_key), urls, _file_paths(files))
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

    def run_extraction(run_id: str, api_key: str):
        run_id = _require_run(run_id)
        ledger = workflow.extract(run_id, credentials(api_key))
        return _json(ledger), _flow_html(store, run_id)

    def run_guide(run_id: str, api_key: str):
        run_id = _require_run(run_id)
        guide = workflow.write_guide(run_id, credentials(api_key))
        return guide, _flow_html(store, run_id)

    def run_design(run_id: str, api_key: str):
        run_id = _require_run(run_id)
        design = workflow.design(run_id, credentials(api_key))
        return _json(design), _flow_html(store, run_id)

    def run_author(run_id: str, api_key: str):
        run_id = _require_run(run_id)
        items = workflow.author(run_id, credentials(api_key))
        return _json(items), _flow_html(store, run_id)

    def run_visual_plan(run_id: str, api_key: str):
        run_id = _require_run(run_id)
        plan = workflow.plan_visuals(run_id, credentials(api_key))
        return _json(plan), _flow_html(store, run_id)

    def run_images(run_id: str, api_key: str):
        run_id = _require_run(run_id)
        ledger = workflow.generate_images(run_id, credentials(api_key))
        return _json(ledger), _flow_html(store, run_id)

    def run_validation(run_id: str):
        run_id = _require_run(run_id)
        report = workflow.validate(run_id)
        return _json(report), _flow_html(store, run_id)

    def run_review(run_id: str, api_key: str):
        run_id = _require_run(run_id)
        review = workflow.semantic_review(run_id, credentials(api_key))
        report = store.read_json(run_id, "validation/validation-report.json")
        return _json(review), _json(report), _flow_html(store, run_id)

    def run_export(run_id: str):
        run_id = _require_run(run_id)
        target = workflow.export(run_id)
        download_dir = Path(tempfile.mkdtemp(prefix="knowledge-pack-studio-"))
        download_target = download_dir / target.name
        shutil.copy2(target, download_target)
        return str(download_target), _flow_html(store, run_id)

    def load_run(selected: str):
        run_id = selected or ""
        return run_id, _flow_html(store, run_id)

    with gr.Blocks(title="Knowledge Pack Studio") as app:
        gr.HTML(
            """<div class="kp-hero"><h1>Knowledge Pack Studio</h1>
            <p>Turn an idea into an evidence-led FlashFeed pack through explicit research,
            extraction, study, design, authoring, visual, and validation stages.</p></div>"""
        )
        gr.HTML(
            """<div class="kp-warning"><strong>Credential policy:</strong> keys are passed to the
            current Colab/Python process only. They are not written into run artifacts or exports.
            Mock mode requires no key and can never pass the publication gate.</div>"""
        )
        flow = gr.HTML(_flow_html(store, None))
        with gr.Row():
            run_id = gr.Textbox(label="Current run ID", interactive=False, scale=3)
            recent = gr.Dropdown(
                choices=store.list_runs(), label="Resume a run", allow_custom_value=False, scale=2
            )
            load_button = gr.Button("Load", scale=1)
        with gr.Accordion("Provider and model settings", open=False):
            with gr.Row():
                api_key = gr.Textbox(
                    label="OpenAI API key",
                    type="password",
                    placeholder="Stored only in this active UI session",
                )
                mock_mode = gr.Checkbox(label="Mock demonstration mode", value=True)
            config_json = gr.Code(
                value=default_config,
                language="json",
                label="Versioned run configuration",
            )

        with gr.Tabs():
            with gr.Tab("1 · Idea and brief"):
                idea = gr.Textbox(
                    label="Idea",
                    lines=4,
                    placeholder="What should someone understand or be able to do?",
                )
                with gr.Row():
                    audience = gr.Textbox(label="Audience", value="Curious adult beginners")
                    outcomes = gr.Textbox(label="Desired outcomes (one per line)", lines=3)
                    constraints = gr.Textbox(label="Constraints (one per line)", lines=3)
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

            with gr.Tab("2 · Research and extraction"):
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

            with gr.Tab("3 · Study guide and design"):
                guide_button = gr.Button("Write study guide", variant="primary")
                guide_markdown = gr.Markdown()
                design_button = gr.Button("Create pack design")
                design_json = gr.Code(label="Pack design", language="json")

            with gr.Tab("4 · Author and visuals"):
                author_button = gr.Button("Author seed items", variant="primary")
                items_json = gr.Code(label="Authored items", language="json")
                visual_button = gr.Button("Plan instructional visuals")
                visual_json = gr.Code(label="Visual plan", language="json")
                image_button = gr.Button("Generate approved images")
                image_json = gr.Code(label="Image ledger", language="json")

            with gr.Tab("5 · Validate, review, and export"):
                validate_button = gr.Button("Run deterministic validation", variant="primary")
                validation_json = gr.Code(label="Validation report", language="json")
                review_button = gr.Button("Run independent semantic review")
                review_json = gr.Code(label="Semantic review", language="json")
                export_button = gr.Button("Build portable bundle")
                bundle_file = gr.File(label="Knowledge-pack bundle")

        create_button.click(
            create_and_clarify,
            [idea, audience, outcomes, constraints, config_json, mock_mode, api_key],
            [run_id, brief_draft, questions, flow],
        )
        approve_button.click(approve, [run_id, answers], [approved_brief, flow])
        research_button.click(
            run_research,
            [run_id, api_key, source_urls, uploads],
            [research_report, source_table, flow],
        )
        extraction_button.click(run_extraction, [run_id, api_key], [evidence_json, flow])
        guide_button.click(run_guide, [run_id, api_key], [guide_markdown, flow])
        design_button.click(run_design, [run_id, api_key], [design_json, flow])
        author_button.click(run_author, [run_id, api_key], [items_json, flow])
        visual_button.click(run_visual_plan, [run_id, api_key], [visual_json, flow])
        image_button.click(run_images, [run_id, api_key], [image_json, flow])
        validate_button.click(run_validation, [run_id], [validation_json, flow])
        review_button.click(
            run_review,
            [run_id, api_key],
            [review_json, validation_json, flow],
        )
        export_button.click(run_export, [run_id], [bundle_file, flow])
        load_button.click(load_run, [recent], [run_id, flow])

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
    app = build_app(run_root, default_api_key=api_key)
    return app.launch(
        share=share,
        inline=True,
        show_error=True,
        css=CSS,
        theme=gr.themes.Base(),
        **launch_kwargs,
    )
