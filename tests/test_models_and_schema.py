from __future__ import annotations

import ast
import hashlib
import json
import subprocess
import sys
from pathlib import Path

import nbformat
import pytest

from knowledge_pack_studio.config import StudioConfig
from knowledge_pack_studio.models import ItemDraft, RunManifest, VisualBrief
from knowledge_pack_studio.schema_loader import pack_schema_path
from knowledge_pack_studio.ui import _prepare_launch_kwargs, _validate_share_auth, build_app

EXPECTED_PACK_SCHEMA_SHA256 = "7138d6ec4ce84679376e22b830bf8d4267815aea722210feec52f8cb22355413"


def test_canonical_schema_checksum_is_pinned():
    digest = hashlib.sha256(pack_schema_path().read_bytes()).hexdigest()
    assert digest == EXPECTED_PACK_SCHEMA_SHA256


def test_notebook_is_valid_and_has_colab_metadata():
    notebook_path = Path(__file__).resolve().parents[1] / "notebooks/Knowledge_Pack_Studio.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    assert notebook.metadata.colab.name == "Knowledge Pack Studio"
    notebook_source = "\n".join("".join(cell.source) for cell in notebook.cells)
    assert "launch(api_key=api_key, share=False, debug=True)" in notebook_source
    assert "There is no separate error-display setting to find" in notebook_source
    assert '"--force-reinstall"' in notebook_source
    assert "Exact build details will appear in the launch cell" in notebook_source
    assert 'COLAB_SECRET_NAME = "OPENAI_API_KEY_FF_KP"' in notebook_source
    assert "FF_KP_STUDIO_PASSWORD" not in notebook_source
    assert "userdata.get('OPENAI_API_KEY')" not in notebook_source
    assert "enter a key in the Studio UI" not in notebook_source


def test_pipeline_version_identifies_the_refreshed_colab_build():
    assert StudioConfig().pipeline_version == "0.2.0.dev0"


def test_native_notebook_is_valid_headless_and_self_contained():
    notebook_path = Path(__file__).resolve().parents[1] / "notebooks/Knowledge_Pack_Studio_v2.ipynb"
    notebook = nbformat.read(notebook_path, as_version=4)
    nbformat.validate(notebook)
    assert notebook.metadata.colab.name == "Knowledge Pack Studio v0.2"
    source = "\n".join("".join(cell.source) for cell in notebook.cells)
    assert "NotebookStudio" in source
    assert "OPENAI_API_KEY_FF_KP" in source
    assert 'STUDIO_PREVIEW_REVISION = "agent/native-notebook-codespaces-v02"' in source
    assert 'name.startswith("knowledge_pack_studio.")' in source
    assert '"event_sink" not in artifact_store_parameters' in source
    assert "studio.clarification_interview()" in source
    assert "Copy these required IDs into ANSWERS" not in source
    assert "source first" in source
    assert "studio.design()" in source
    assert source.index("studio.design()") < source.index("studio.write_guide()")
    assert "gradio" not in source.lower()
    for cell in notebook.cells:
        if cell.cell_type == "code":
            ast.parse(cell.source)


def test_core_import_does_not_load_the_legacy_ui_dependency():
    completed = subprocess.run(
        [
            sys.executable,
            "-c",
            "import sys, knowledge_pack_studio; print('gradio' in sys.modules)",
        ],
        check=True,
        capture_output=True,
        text=True,
    )
    assert completed.stdout.strip() == "False"


def test_item_shape_validation_rejects_incomplete_mcq():
    with pytest.raises(ValueError):
        ItemDraft(
            item_id="broken",
            part_id="part-one",
            claim_ids=["claim-one"],
            shape="mcq",
            tags=[],
            prompt="Question?",
            options=["Only one"],
            correct_index=0,
        )


def test_legacy_visual_targets_upgrade_to_a_list():
    brief = VisualBrief.model_validate(
        {
            "asset_id": "asset-one",
            "item_id": "item-one, item-two",
            "teaching_purpose": "Compare two related examples",
            "kind": "photo",
            "prompt": "A relevant instructional photograph",
            "search_term": "relevant examples",
            "alt_text": "Two related examples shown side by side",
            "generate": False,
        }
    )
    assert brief.item_ids == ["item-one", "item-two"]


def test_pipeline_schemas_are_machine_readable():
    root = Path(__file__).resolve().parents[1] / "schema"
    for filename in (
        "brief.schema.json",
        "research-dossier.schema.json",
        "evidence-ledger.schema.json",
        "pack-design.schema.json",
        "authored-items.schema.json",
        "visual-plan.schema.json",
        "validation-report.schema.json",
        "semantic-review.schema.json",
        "run-manifest.schema.json",
        "pack.schema.json",
    ):
        data = json.loads((root / filename).read_text())
        assert data.get("$schema") or data.get("type") == "object"


def test_public_share_requires_authentication():
    with pytest.raises(RuntimeError, match="require authentication"):
        _validate_share_auth(True, None)

    _validate_share_auth(True, ("ff-kp-author", "test-password"))
    _validate_share_auth(False, None)


def test_private_colab_launch_uses_authenticated_proxy_for_assets_and_logs():
    proxy_calls: list[int] = []

    def proxy_url(port: int) -> str:
        proxy_calls.append(port)
        return "https://private-colab-proxy.example/"

    prepared = _prepare_launch_kwargs(
        {"server_port": 8123},
        is_colab=True,
        share=False,
        proxy_url_getter=proxy_url,
    )

    assert proxy_calls == [8123]
    assert prepared["root_path"] == "https://private-colab-proxy.example"
    assert prepared["debug"] is True
    assert prepared["height"] == 900


def test_local_and_public_launches_do_not_request_a_colab_proxy():
    def unexpected_proxy(_: int) -> str:
        raise AssertionError("proxy URL should not be requested")

    assert _prepare_launch_kwargs(
        {"debug": False},
        is_colab=False,
        share=False,
        proxy_url_getter=unexpected_proxy,
    ) == {"debug": False}
    assert _prepare_launch_kwargs(
        {"auth": ("author", "password")},
        is_colab=True,
        share=True,
        proxy_url_getter=unexpected_proxy,
    ) == {"auth": ("author", "password")}


def test_ui_reports_credential_state_without_rendering_a_key_input(tmp_path):
    marker = "sk-test-key-that-must-stay-server-side"
    app = build_app(tmp_path / "runs", default_api_key=marker)
    config = json.dumps(app.get_config_file())

    assert marker not in config
    assert "OpenAI API key" not in config
    assert "OpenAI credential connected" in config
    assert "Live run activity and agent log" in config
    assert "Running build:" in config
    assert "Refresh activity" in config
    assert '"value": 5.0' in config


def test_old_manifests_load_with_an_empty_activity_log():
    manifest = RunManifest.model_validate(
        {
            "run_id": "legacy-run",
            "created_at": "2026-08-04T00:00:00+00:00",
            "updated_at": "2026-08-04T00:00:00+00:00",
            "status": "active",
            "pipeline_version": "0.1.0.dev0",
            "schema_version": "0.3.0",
            "provider": "openai",
            "mock": True,
            "stages": {},
            "artifacts": {},
            "agent_calls": [],
        }
    )

    assert manifest.events == []
