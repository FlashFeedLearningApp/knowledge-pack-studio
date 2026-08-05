"""Adapter for the open-source Image Source-cery command-line pipeline."""

from __future__ import annotations

import json
import os
import subprocess
import tempfile
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class SourcedImage:
    payload: bytes
    extension: str
    provenance: dict


def _extension(payload: bytes) -> str:
    if payload.startswith(b"\x89PNG\r\n\x1a\n"):
        return ".png"
    if payload.startswith(b"\xff\xd8\xff"):
        return ".jpg"
    if payload[:4] in {b"RIFF"} and payload[8:12] == b"WEBP":
        return ".webp"
    return ".img"


def source_image(
    query: str,
    *,
    command: list[str],
    providers: list[str],
    judge: str,
    credentials: dict[str, str],
) -> SourcedImage:
    """Run one ranked source-first acquisition and return bytes plus provenance."""

    environment = os.environ.copy()
    if credentials.get("default"):
        environment["OPENAI_API_KEY"] = credentials["default"]
    for name in (
        "UNSPLASH_ACCESS_KEY",
        "PEXELS_API_KEY",
        "SMITHSONIAN_API_KEY",
    ):
        if credentials.get(name):
            environment[name] = credentials[name]

    with tempfile.TemporaryDirectory(prefix="ff-kp-image-") as temporary:
        target = Path(temporary) / "candidate.download"
        args = [
            *command,
            "find",
            query,
            "--out",
            str(target),
            "--providers",
            ",".join(providers),
            "--judge",
            judge,
        ]
        completed = subprocess.run(
            args,
            check=False,
            capture_output=True,
            text=True,
            env=environment,
        )
        if completed.returncode != 0 or not target.is_file():
            detail = completed.stderr.strip() or completed.stdout.strip() or "no candidate returned"
            raise RuntimeError(f"Image Source-cery could not acquire '{query}': {detail[-1000:]}")
        sidecar = target.with_name(target.name + ".json")
        provenance = (
            json.loads(sidecar.read_text(encoding="utf-8"))
            if sidecar.is_file()
            else json.loads(completed.stdout)
        )
        payload = target.read_bytes()
        return SourcedImage(payload, _extension(payload), provenance)
