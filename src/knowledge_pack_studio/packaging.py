"""Create a portable publishable pack plus its audit evidence."""

from __future__ import annotations

import hashlib
import zipfile
from pathlib import Path

from .schema_loader import schema_path

AUDIT_SCHEMAS = (
    "pack.schema.json",
    "brief.schema.json",
    "research-dossier.schema.json",
    "evidence-ledger.schema.json",
    "pack-design.schema.json",
    "authored-items.schema.json",
    "visual-plan.schema.json",
    "validation-report.schema.json",
    "semantic-review.schema.json",
    "run-manifest.schema.json",
)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def export_bundle(run_dir: Path, pack_id: str, publishable: bool) -> Path:
    exports = run_dir / "exports"
    exports.mkdir(parents=True, exist_ok=True)
    target = exports / f"{pack_id}-knowledge-pack-bundle.zip"
    publishable_root = run_dir / "publishable" / pack_id
    audit_files = {
        "audit/run-manifest.json": run_dir / "run-manifest.json",
        "audit/configuration.json": run_dir / "configuration.json",
        "audit/research-dossier.json": run_dir / "research/research-dossier.json",
        "audit/evidence-ledger.json": run_dir / "evidence/evidence-ledger.json",
        "audit/pack-design.json": run_dir / "design/pack-design.json",
        "audit/item-ledger.json": run_dir / "items/item-ledger.json",
        "audit/visual-plan.json": run_dir / "visuals/visual-plan.json",
        "audit/image-ledger.json": run_dir / "visuals/image-ledger.json",
        "audit/validation-report.json": run_dir / "validation/validation-report.json",
        "audit/semantic-review.json": run_dir / "validation/semantic-review.json",
    }
    audit_files.update(
        {f"audit/schema/{filename}": schema_path(filename) for filename in AUDIT_SCHEMAS}
    )
    files: dict[str, Path] = {}
    for path in publishable_root.rglob("*"):
        if path.is_file():
            files[f"publishable/{pack_id}/{path.relative_to(publishable_root)}"] = path
    files.update({name: path for name, path in audit_files.items() if path.is_file()})
    sums = "\n".join(f"{_sha(path)}  {name}" for name, path in sorted(files.items())) + "\n"
    status = "PUBLISHABLE" if publishable else "DRAFT — validation or review gates remain"
    bundle_readme = f"""# Knowledge Pack Authoring Bundle

Status: **{status}**

- `publishable/{pack_id}/` contains the FlashFeed consumer-facing pack.
- `audit/` contains the pinned schema, evidence, design, validation, and run provenance.
- `SHA256SUMS` records a checksum for every bundled artifact.

This bundle does not contain API keys. A draft status must not be treated as release approval.
"""
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for name, path in sorted(files.items()):
            archive.write(path, name)
        archive.writestr("README.md", bundle_readme)
        archive.writestr("SHA256SUMS", sums)
    return target
