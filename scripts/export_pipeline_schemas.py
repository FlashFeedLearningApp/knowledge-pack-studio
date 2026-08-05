"""Regenerate versioned pipeline-artifact schemas from Pydantic models."""

from __future__ import annotations

import json
from pathlib import Path

from knowledge_pack_studio.models import ApprovedBrief, EvidenceLedger


def main() -> None:
    root = Path(__file__).resolve().parents[1] / "schema"
    root.mkdir(parents=True, exist_ok=True)
    rows = {
        "brief.schema.json": ApprovedBrief.model_json_schema(),
        "evidence-ledger.schema.json": EvidenceLedger.model_json_schema(),
    }
    for filename, schema in rows.items():
        (root / filename).write_text(
            json.dumps(schema, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )


if __name__ == "__main__":
    main()
