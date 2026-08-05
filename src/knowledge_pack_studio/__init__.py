"""Public entry points for Knowledge Pack Studio.

The core package deliberately avoids importing Gradio. The legacy browser UI remains available
through lazy wrappers so notebooks, Codespaces, and command-line automation share a lightweight
headless engine.
"""

from typing import Any

from .notebook import NotebookStudio
from .workflow import StudioWorkflow

__all__ = ["NotebookStudio", "StudioWorkflow", "build_app", "launch"]
__version__ = "0.2.0.dev0"


def build_app(*args: Any, **kwargs: Any) -> Any:
    """Build the optional legacy Gradio interface without importing it in headless sessions."""

    from .ui import build_app as legacy_build_app

    return legacy_build_app(*args, **kwargs)


def launch(*args: Any, **kwargs: Any) -> Any:
    """Launch the optional legacy Gradio interface."""

    from .ui import launch as legacy_launch

    return legacy_launch(*args, **kwargs)
