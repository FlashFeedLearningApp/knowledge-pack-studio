"""Local and CI entry points."""

from __future__ import annotations

import argparse
import os
from pathlib import Path

from .store import ArtifactStore
from .workflow import StudioWorkflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Run Knowledge Pack Studio")
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--server-port", type=int, default=None)
    parser.add_argument(
        "--smoke-run", action="store_true", help="Run the deterministic mock pipeline"
    )
    parser.add_argument(
        "--legacy-ui",
        action="store_true",
        help="Launch the optional legacy Gradio prototype",
    )
    args = parser.parse_args()
    if args.smoke_run:
        workflow = StudioWorkflow(ArtifactStore(args.run_root))
        run_id = workflow.run_all_mock()
        print(workflow.store.load_manifest(run_id).final_bundle_path)
        return
    if not args.legacy_ui:
        parser.error("choose --smoke-run or --legacy-ui; the primary experience is the notebook")
    try:
        from .ui import launch
    except ImportError as exc:
        raise RuntimeError(
            "The legacy UI is optional. Install it with: pip install -e '.[legacy-ui]'"
        ) from exc
    kwargs = {"server_port": args.server_port} if args.server_port else {}
    launch(
        api_key=os.environ.get("OPENAI_API_KEY_FF_KP"),
        run_root=args.run_root,
        share=args.share,
        **kwargs,
    )


if __name__ == "__main__":
    main()
