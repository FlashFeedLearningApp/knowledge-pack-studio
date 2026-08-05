"""Locate and load the pinned portable consumer schema."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any


def pack_schema_path() -> Path:
    installed = resources.files("knowledge_pack_studio").joinpath("schema/pack.schema.json")
    try:
        candidate = Path(str(installed))
        if candidate.exists():
            return candidate
    except TypeError:
        pass
    source_checkout = Path(__file__).resolve().parents[2] / "schema" / "pack.schema.json"
    if source_checkout.exists():
        return source_checkout
    raise FileNotFoundError("The pinned FlashFeed pack.schema.json could not be located")


def load_pack_schema() -> dict[str, Any]:
    return json.loads(pack_schema_path().read_text(encoding="utf-8"))
