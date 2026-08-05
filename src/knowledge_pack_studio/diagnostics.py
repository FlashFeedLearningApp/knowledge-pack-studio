"""Portable, credential-scrubbed diagnostics for an authoring run."""

from __future__ import annotations

import importlib.metadata
import json
import platform
import re
import tempfile
import zipfile
from pathlib import Path

from .store import ArtifactStore

SECRET_PATTERNS = (
    re.compile(r"\bsk-[A-Za-z0-9_-]{8,}\b"),
    re.compile(r"\bBearer\s+[A-Za-z0-9._-]{8,}\b", re.IGNORECASE),
)


def redact_secrets(text: str) -> str:
    for pattern in SECRET_PATTERNS:
        text = pattern.sub("[REDACTED]", text)
    return text


def _package_version(name: str) -> str | None:
    try:
        return importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError:
        return None


def build_diagnostics_bundle(
    store: ArtifactStore, run_id: str, destination: str | Path | None = None
) -> Path:
    """Bundle reproducibility metadata and textual artifacts without stored credentials."""

    run_dir = store.run_dir(run_id)
    if not (run_dir / "run-manifest.json").is_file():
        raise FileNotFoundError(f"Run does not exist: {run_id}")

    output_dir = (
        Path(destination)
        if destination
        else Path(tempfile.mkdtemp(prefix="knowledge-pack-studio-diagnostics-"))
    )
    output_dir.mkdir(parents=True, exist_ok=True)
    target = output_dir / f"{run_id}-diagnostics.zip"

    environment = {
        "python": platform.python_version(),
        "platform": platform.platform(),
        "packages": {
            name: _package_version(name)
            for name in (
                "flashfeed-knowledge-pack-studio",
                "gradio",
                "openai",
                "pydantic",
            )
        },
    }
    readme = """# Knowledge Pack Studio diagnostics

This bundle contains the run manifest, configuration, recorded stage errors, and the run's textual
JSON/Markdown artifacts. OpenAI API key and bearer-token patterns are redacted, and the Studio does
not persist the Colab password.

The bundle may still contain the author's idea, research text, source URLs, and generated learning
content. Review it before sharing publicly.
"""

    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr("README.md", readme)
        archive.writestr("environment.json", json.dumps(environment, indent=2, sort_keys=True))
        for path in sorted(run_dir.rglob("*")):
            if not path.is_file() or path.suffix.lower() not in {".json", ".md"}:
                continue
            relative = path.relative_to(run_dir)
            archive.writestr(
                f"run/{relative.as_posix()}",
                redact_secrets(path.read_text(encoding="utf-8", errors="replace")),
            )
    return target
