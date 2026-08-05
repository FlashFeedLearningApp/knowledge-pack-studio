from __future__ import annotations

import hashlib
import json
from pathlib import Path

import nbformat
import pytest

from knowledge_pack_studio.models import ItemDraft
from knowledge_pack_studio.schema_loader import pack_schema_path
from knowledge_pack_studio.ui import _validate_share_auth, build_app

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
    assert "launch(api_key=api_key, auth=auth)" in notebook_source
    assert "COLAB_SECRET_NAME = 'OPENAI_API_KEY_FF_KP'" in notebook_source
    assert "COLAB_PASSWORD_SECRET_NAME = 'FF_KP_STUDIO_PASSWORD'" in notebook_source
    assert "userdata.get('OPENAI_API_KEY')" not in notebook_source
    assert "enter a key in the Studio UI" not in notebook_source


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


def test_pipeline_schemas_are_machine_readable():
    root = Path(__file__).resolve().parents[1] / "schema"
    for filename in ("brief.schema.json", "evidence-ledger.schema.json", "pack.schema.json"):
        data = json.loads((root / filename).read_text())
        assert data.get("$schema") or data.get("type") == "object"


def test_public_share_requires_authentication():
    with pytest.raises(RuntimeError, match="require authentication"):
        _validate_share_auth(True, None)

    _validate_share_auth(True, ("ff-kp-author", "test-password"))
    _validate_share_auth(False, None)


def test_ui_reports_credential_state_without_rendering_a_key_input(tmp_path):
    marker = "sk-test-key-that-must-stay-server-side"
    app = build_app(tmp_path / "runs", default_api_key=marker)
    config = json.dumps(app.get_config_file())

    assert marker not in config
    assert "OpenAI API key" not in config
    assert "OpenAI credential connected" in config
