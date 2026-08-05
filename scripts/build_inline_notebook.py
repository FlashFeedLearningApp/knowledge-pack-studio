"""Build the checked-in native Colab/Codespaces notebook."""

from __future__ import annotations

from pathlib import Path
from textwrap import dedent

import nbformat

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "notebooks/Knowledge_Pack_Studio_v2.ipynb"


def md(source: str):
    return nbformat.v4.new_markdown_cell(dedent(source).strip())


def code(source: str):
    return nbformat.v4.new_code_cell(dedent(source).strip())


def main() -> None:
    notebook = nbformat.v4.new_notebook()
    notebook.metadata = {
        "colab": {"name": "Knowledge Pack Studio v0.2", "provenance": []},
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "version": "3.12"},
    }
    notebook.cells = [
        md(
            """
            # FlashFeed Knowledge Pack Studio v0.2

            A native, stage-by-stage authoring notebook. Every cell leaves a readable result,
            every stage checkpoints to disk, and a stopped session can resume from its run ID.

            **Credential policy:** your keys stay in this Python process and are never written to
            run artifacts, diagnostics, or exports. Live mode can incur charges. Mock mode needs no
            key and can never pass the publication gate.

            Run the cells from top to bottom. Review the result of each numbered section before
            continuing.
            """
        ),
        md("## 0 · Install the Studio and optional source-first image tool"),
        code(
            """
            # @title Install or refresh dependencies
            import subprocess
            import sys
            from importlib.metadata import version
            from pathlib import Path

            STUDIO_REPOSITORY = "https://github.com/FlashFeedLearningApp/knowledge-pack-studio.git"
            STUDIO_PRIMARY_REVISION = "main"
            STUDIO_PREVIEW_REVISION = "agent/native-notebook-codespaces-v02"
            IMAGE_REPOSITORY = "https://github.com/garygeo-19/image-sourcery.git"
            IMAGE_REVISION = "5fc6ce4da1ca6ba869abc065a9495b5f6c92b73b"
            INSTALL_IMAGE_SOURCERY = True  # @param {type:"boolean"}

            repository_root = Path.cwd()
            in_source_checkout = (repository_root / "pyproject.toml").is_file()
            if in_source_checkout:
                subprocess.run(
                    [sys.executable, "-m", "pip", "install", "-q", "-e", "."], check=True
                )
            else:
                def install_studio(revision):
                    subprocess.run(
                        [
                            sys.executable,
                            "-m",
                            "pip",
                            "install",
                            "-q",
                            "--upgrade",
                            "--force-reinstall",
                            "--no-cache-dir",
                            f"git+{STUDIO_REPOSITORY}@{revision}",
                        ],
                        check=True,
                    )

                install_studio(STUDIO_PRIMARY_REVISION)
                installed_parts = version("flashfeed-knowledge-pack-studio").split(".")
                installed_series = tuple(int(value) for value in installed_parts[:2])
                if installed_series < (0, 2):
                    print(
                        "main does not contain the v0.2 notebook engine yet; "
                        f"installing preview revision {STUDIO_PREVIEW_REVISION}"
                    )
                    install_studio(STUDIO_PREVIEW_REVISION)

            IMAGE_SOURCERY_COMMAND = None
            if INSTALL_IMAGE_SOURCERY:
                tools_root = (
                    repository_root / ".tools"
                    if in_source_checkout
                    else Path("/content/ff-kp-tools")
                )
                image_root = tools_root / "image-sourcery"
                tools_root.mkdir(parents=True, exist_ok=True)
                if not (image_root / ".git").is_dir():
                    subprocess.run(
                        ["git", "clone", "--filter=blob:none", IMAGE_REPOSITORY, str(image_root)],
                        check=True,
                    )
                subprocess.run(
                    ["git", "-C", str(image_root), "fetch", "--depth", "1", "origin", IMAGE_REVISION],
                    check=True,
                )
                subprocess.run(
                    ["git", "-C", str(image_root), "checkout", "--detach", IMAGE_REVISION],
                    check=True,
                )
                subprocess.run(["npm", "--prefix", str(image_root), "ci", "--silent"], check=True)
                subprocess.run(
                    ["npm", "--prefix", str(image_root), "run", "build", "--silent"], check=True
                )
                IMAGE_SOURCERY_COMMAND = ["node", str(image_root / "dist/cli.js")]

            installed_version = version("flashfeed-knowledge-pack-studio")
            print(f"Studio {installed_version} installed")
            print("Image Source-cery ready" if IMAGE_SOURCERY_COMMAND else "Image sourcing disabled")
            print(
                "If an earlier setup cell already produced an import error in this runtime, "
                "re-run section 1. It will reload the refreshed package; restart the runtime "
                "only if section 1 explicitly asks you to."
            )
            """
        ),
        md("## 1 · Connect credentials and checkpoint storage"),
        code(
            """
            # @title Create this notebook session
            import json
            import os
            from pathlib import Path

            import importlib
            from importlib.metadata import version

            from IPython.display import JSON, Markdown, display

            import knowledge_pack_studio as studio_package

            if not hasattr(studio_package, "NotebookStudio"):
                importlib.invalidate_caches()
                studio_package = importlib.reload(studio_package)
            if not hasattr(studio_package, "NotebookStudio"):
                raise RuntimeError(
                    "The pre-v0.2 package is still cached. Choose Runtime → Restart session, "
                    "then run sections 0 and 1 again."
                )
            NotebookStudio = studio_package.NotebookStudio
            print(
                "Loaded Studio",
                version("flashfeed-knowledge-pack-studio"),
                "from",
                studio_package.__file__,
            )

            USE_GOOGLE_DRIVE = True  # @param {type:"boolean"}
            COLAB_SECRET_NAME = "OPENAI_API_KEY_FF_KP"

            def read_secret(name):
                try:
                    from google.colab import userdata
                    return userdata.get(name)
                except Exception:
                    return os.environ.get(name)

            try:
                from google.colab import drive
                IN_COLAB = True
            except ImportError:
                IN_COLAB = False

            if IN_COLAB and USE_GOOGLE_DRIVE:
                drive.mount("/content/drive")
                RUN_ROOT = Path("/content/drive/MyDrive/FlashFeed/KnowledgePackStudio/runs")
            else:
                RUN_ROOT = Path.cwd() / "runs"

            credentials = {
                "default": read_secret(COLAB_SECRET_NAME),
                "UNSPLASH_ACCESS_KEY": read_secret("UNSPLASH_ACCESS_KEY"),
                "PEXELS_API_KEY": read_secret("PEXELS_API_KEY"),
                "SMITHSONIAN_API_KEY": read_secret("SMITHSONIAN_API_KEY"),
            }
            # Optional advanced routing: profile name -> Colab/Codespaces secret name.
            # Then assign that profile to an agent in AGENT_CREDENTIAL_PROFILES in section 2.
            AGENT_SECRET_NAMES = {
                # "research-key": "OPENAI_API_KEY_FF_KP_RESEARCH",
                # "review-key": "OPENAI_API_KEY_FF_KP_REVIEW",
            }
            for profile_name, secret_name in AGENT_SECRET_NAMES.items():
                credentials[profile_name] = read_secret(secret_name)
            credentials = {name: value for name, value in credentials.items() if value}
            studio = NotebookStudio(RUN_ROOT, credentials=credentials, echo_progress=True)

            print(f"Run storage: {RUN_ROOT}")
            print(
                "Live OpenAI credential connected"
                if studio.live_mode_ready
                else "No OpenAI credential connected — use mock mode or add OPENAI_API_KEY_FF_KP"
            )
            print("No credential values are displayed or persisted.")
            """
        ),
        md(
            """
            ## 2 · Start with an idea, or resume a run

            For a new run, edit the form values and run the cell. To continue a saved project,
            choose **resume latest** or paste a run ID. The complete artifact workspace is restored,
            not just the pipeline position.
            """
        ),
        code(
            """
            # @title Start or resume
            from knowledge_pack_studio.config import StudioConfig

            ACTION = "new"  # @param ["new", "resume latest", "resume by ID"]
            RUN_ID_TO_RESUME = ""  # @param {type:"string"}
            RUN_MODE = "live"  # @param ["live", "mock"]
            IDEA = "Build a practical introduction to..."  # @param {type:"string"}
            AUDIENCE = "Curious adult beginners"  # @param {type:"string"}
            DESIRED_OUTCOMES = ""  # @param {type:"string"}
            CONSTRAINTS = ""  # @param {type:"string"}
            TARGET_ITEM_COUNT = 48  # @param {type:"integer"}

            # Optional advanced routing. Unlisted agents keep the documented defaults.
            AGENT_MODEL_OVERRIDES = {
                # "researcher": "gpt-5.6-sol",
                # "guide_author": "gpt-5.6-terra",
            }
            AGENT_CREDENTIAL_PROFILES = {
                # "researcher": "research-key",
                # "reviewer": "review-key",
            }

            if ACTION == "new":
                config = StudioConfig(target_item_count=TARGET_ITEM_COUNT)
                for agent_name, model_name in AGENT_MODEL_OVERRIDES.items():
                    config.agents[agent_name].model = model_name
                for agent_name, profile_name in AGENT_CREDENTIAL_PROFILES.items():
                    config.agents[agent_name].credential = profile_name
                run_id = studio.create_run(IDEA, config=config, mock=RUN_MODE == "mock")
                intake = {
                    "audience": AUDIENCE,
                    "desired_outcomes": [
                        line.strip() for line in DESIRED_OUTCOMES.splitlines() if line.strip()
                    ],
                    "constraints": [
                        line.strip() for line in CONSTRAINTS.splitlines() if line.strip()
                    ],
                }
                brief = studio.clarify(intake)
                display(JSON(brief.model_dump(mode="json"), expanded=False))
            elif ACTION == "resume by ID":
                run_id = studio.resume(RUN_ID_TO_RESUME.strip())
            else:
                run_id = studio.resume()

            studio.show_status()
            """
        ),
        md("## 3 · Answer clarification questions and approve the brief"),
        code(
            """
            # @title Review and approve (edit ANSWERS when questions are shown)
            APPROVE_BRIEF = False  # @param {type:"boolean"}
            ANSWERS = {
                # "question-id": "Your answer",
            }

            questions = studio.clarification_questions()
            if questions:
                display(Markdown("### Clarification questions"))
                display(JSON(questions, expanded=True))
                template = {row["question_id"]: "" for row in questions if row["required"]}
                print("Copy these required IDs into ANSWERS and add your responses:")
                print(json.dumps(template, indent=2))
            else:
                print("The brief has no unanswered clarification questions.")

            if APPROVE_BRIEF:
                approved = studio.approve(ANSWERS)
                display(JSON(approved.model_dump(mode="json"), expanded=False))
                print("Brief approved. Continue to grounded research.")
            else:
                print("Approval is OFF. Review the brief, then set APPROVE_BRIEF to True and re-run.")
            studio.show_status()
            """
        ),
        md(
            """
            ## 4 · Grounded research

            The research specialist uses OpenAI web search plus any URLs or local files you supply.
            It produces a source inventory and a research dossier; it does not author lessons yet.
            """
        ),
        code(
            """
            # @title Research the approved brief
            SOURCE_URLS = ""  # @param {type:"string"}
            LOCAL_FILE_PATHS = ""  # @param {type:"string"}

            dossier = studio.research(
                source_urls=[line.strip() for line in SOURCE_URLS.splitlines() if line.strip()],
                file_paths=[line.strip() for line in LOCAL_FILE_PATHS.splitlines() if line.strip()],
            )
            display(Markdown(dossier.report_markdown))
            display(JSON([source.model_dump(mode="json") for source in dossier.sources], expanded=False))
            studio.show_status()
            """
        ),
        md("## 5 · Extract claim-level evidence"),
        code(
            """
            # @title Build the evidence ledger
            evidence = studio.extract()
            display(JSON(evidence.model_dump(mode="json"), expanded=False))
            print(f"Approved claims: {sum(c.approved_for_instruction for c in evidence.claims)} / {len(evidence.claims)}")
            studio.show_status()
            """
        ),
        md(
            """
            ## 6 · Plan lessons and parts before writing prose

            This blueprint is the curriculum contract: broad topics should become multiple lessons,
            lessons should contain 2–4 coherent parts, and each part targets 6–10 final items.
            """
        ),
        code(
            """
            # @title Create the curriculum and item blueprint
            design = studio.design()
            display(JSON(design.model_dump(mode="json"), expanded=False))
            lesson_count = len(design.lessons)
            part_count = sum(len(lesson.parts) for lesson in design.lessons)
            print(f"Planned: {lesson_count} lesson(s), {part_count} part(s), {design.target_item_count} items")
            studio.show_status()
            """
        ),
        md("## 7 · Write the learner-facing study guides"),
        code(
            """
            # @title Write guides from the approved evidence and curriculum plan
            guide_markdown = studio.write_guide()
            display(Markdown(guide_markdown))
            studio.show_status()
            """
        ),
        md("## 8 · Author evidence-linked items and run structural preflight"),
        code(
            """
            # @title Author seed items
            authored = studio.author()
            display(JSON(authored.model_dump(mode="json"), expanded=False))
            print(f"Authored {len(authored.items)} evidence-linked seed items")

            preflight = studio.preflight()
            display(JSON(preflight.model_dump(mode="json"), expanded=False))
            if not preflight.hard_gates_passed:
                print("STOP: repair the blueprint or items before acquiring images.")
            else:
                print("Structural preflight passed. Optional visual work may continue.")
            studio.show_status()
            """
        ),
        md(
            """
            ## 9 · Plan and acquire visuals

            The recommended mode tries open and licensed sources first through Image Source-cery,
            preserving provider, source page, license, attribution, and judge results. Generation is
            an explicit fallback and is never required to finish a pack.
            """
        ),
        code(
            """
            # @title Create the visual plan
            visual_plan = studio.plan_visuals()
            display(JSON(visual_plan.model_dump(mode="json"), expanded=False))
            studio.show_status()
            """
        ),
        code(
            """
            # @title Acquire, generate, or skip images
            IMAGE_STRATEGY = "source first"  # @param ["source first", "generate with OpenAI", "skip"]
            SOURCE_PROVIDERS = "wikimedia,inaturalist,loc,openverse,nasa,met,unsplash,pexels"  # @param {type:"string"}
            SOURCE_JUDGE = "openai"  # @param ["openai", "none"]
            ALLOW_GENERATION_FALLBACK = False  # @param {type:"boolean"}

            if IMAGE_STRATEGY == "source first":
                if not IMAGE_SOURCERY_COMMAND:
                    raise RuntimeError("Re-run section 0 with INSTALL_IMAGE_SOURCERY enabled")
                providers = [name.strip() for name in SOURCE_PROVIDERS.split(",") if name.strip()]
                if ALLOW_GENERATION_FALLBACK and "generate" not in providers:
                    providers.append("generate")
                image_ledger = studio.source_images(
                    command=IMAGE_SOURCERY_COMMAND,
                    providers=providers,
                    judge=SOURCE_JUDGE,
                    confirm_generation_fallback=ALLOW_GENERATION_FALLBACK,
                )
            elif IMAGE_STRATEGY == "generate with OpenAI":
                image_ledger = studio.generate_images(confirm_cost=True)
            else:
                image_ledger = studio.skip_images()

            display(JSON(image_ledger, expanded=False))
            studio.show_status()
            """
        ),
        md("## 10 · Validate, review, and export"),
        code(
            """
            # @title Run deterministic validation and independent semantic review
            validation = studio.validate()
            display(JSON(validation.model_dump(mode="json"), expanded=False))
            review = studio.review()
            display(JSON(review.model_dump(mode="json"), expanded=False))
            studio.show_status()
            """
        ),
        code(
            """
            # @title Export the portable pack bundle
            bundle_path = studio.export()
            print(f"Bundle: {bundle_path}")
            print("Publication status is recorded inside the bundle; failed and mock runs export as DRAFT.")

            DOWNLOAD_BUNDLE = False  # @param {type:"boolean"}
            if DOWNLOAD_BUNDLE:
                try:
                    from google.colab import files
                    files.download(str(bundle_path))
                except ImportError:
                    print("Download from the file explorer:", bundle_path)
            studio.show_status()
            """
        ),
        md("## 11 · Activity log and shareable diagnostics"),
        code(
            """
            # @title Inspect progress or download diagnostics at any time
            studio.show_activity(limit=100)
            diagnostics_path = studio.diagnostics()
            print(f"Diagnostics: {diagnostics_path}")

            DOWNLOAD_DIAGNOSTICS = False  # @param {type:"boolean"}
            if DOWNLOAD_DIAGNOSTICS:
                try:
                    from google.colab import files
                    files.download(str(diagnostics_path))
                except ImportError:
                    print("Download from the file explorer:", diagnostics_path)
            """
        ),
    ]
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    nbformat.write(notebook, TARGET)
    print(TARGET)


if __name__ == "__main__":
    main()
