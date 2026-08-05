"""Locate and load the pinned portable consumer schema."""

from __future__ import annotations

import json
from importlib import resources
from pathlib import Path
from typing import Any


def schema_path(filename: str) -> Path:
    if not filename.endswith(".schema.json") or "/" in filename or "\\" in filename:
        raise ValueError("Schema filename must end in .schema.json")
    installed = resources.files("knowledge_pack_studio").joinpath(f"schema/{filename}")
    try:
        candidate = Path(str(installed))
        if candidate.exists():
            return candidate
    except TypeError:
        pass
    source_checkout = Path(__file__).resolve().parents[2] / "schema" / filename
    if source_checkout.exists():
        return source_checkout
    raise FileNotFoundError(f"The bundled {filename} could not be located")


def pack_schema_path() -> Path:
    return schema_path("pack.schema.json")


def load_pack_schema() -> dict[str, Any]:
    return json.loads(pack_schema_path().read_text(encoding="utf-8"))
