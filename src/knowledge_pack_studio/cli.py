"""Local and CI entry points."""

from __future__ import annotations

import argparse
from pathlib import Path

from .store import ArtifactStore
from .ui import launch
from .workflow import StudioWorkflow


def main() -> None:
    parser = argparse.ArgumentParser(description="Launch or smoke-test Knowledge Pack Studio")
    parser.add_argument("--run-root", type=Path, default=None)
    parser.add_argument("--share", action="store_true")
    parser.add_argument("--server-port", type=int, default=None)
    parser.add_argument(
        "--smoke-run", action="store_true", help="Run the deterministic mock pipeline"
    )
    args = parser.parse_args()
    if args.smoke_run:
        workflow = StudioWorkflow(ArtifactStore(args.run_root))
        run_id = workflow.run_all_mock()
        print(workflow.store.load_manifest(run_id).final_bundle_path)
        return
    kwargs = {"server_port": args.server_port} if args.server_port else {}
    launch(run_root=args.run_root, share=args.share, **kwargs)


if __name__ == "__main__":
    main()
