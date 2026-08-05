# Knowledge Pack Studio

Knowledge Pack Studio is an open-source, bring-your-own-key authoring pipeline for FlashFeed
knowledge packs. It turns an idea into an approved brief, grounded research, claim-level evidence,
a curriculum plan, learner-facing guides, evidence-linked items, sourced or generated visuals,
validation, review, and a portable ZIP bundle.

No shared application server is required. Each author runs the pipeline in a private Colab runtime,
a personal GitHub Codespace, or local Jupyter and pays only for the provider calls made with their
own credentials.

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FlashFeedLearningApp/knowledge-pack-studio/blob/main/notebooks/Knowledge_Pack_Studio_v2.ipynb)
[![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/FlashFeedLearningApp/knowledge-pack-studio?quickstart=1)

> **Development status:** `0.2.0.dev0`. The native notebook and headless engine are ready for
> evaluation. Mock mode is fully offline and deliberately fails the publication gate. Live output
> still needs representative-topic evaluation and upstream consumer testing before a community
> release candidate.

## Choose the easiest entry point

### Colab: quickest for an author

Open [`notebooks/Knowledge_Pack_Studio_v2.ipynb`](notebooks/Knowledge_Pack_Studio_v2.ipynb), copy it
to your Drive if you want your own editable notebook, and run the cells from top to bottom. The
notebook is the interface: there is no separate web server, public tunnel, or second login.

Add `OPENAI_API_KEY_FF_KP` under **Colab → Secrets** and grant the notebook access. The dedicated
name prevents accidentally selecting another OpenAI key. Optional image-source secrets are
`UNSPLASH_ACCESS_KEY`, `PEXELS_API_KEY`, and `SMITHSONIAN_API_KEY`.

By default, run artifacts checkpoint to
`MyDrive/FlashFeed/KnowledgePackStudio/runs/<run-id>/`. A restarted runtime can resume the latest
run or a selected run ID and reload every persisted artifact.

### Codespaces: quickest for a contributor or power user

Use the Codespaces badge, create the environment, then open
[`notebooks/Knowledge_Pack_Studio_v2.ipynb`](notebooks/Knowledge_Pack_Studio_v2.ipynb) in VS Code.
The dev container installs Python, Jupyter, the Studio, Node.js, and the pinned source-first image
tool automatically.

Add `OPENAI_API_KEY_FF_KP` as a Codespaces secret before creating the Codespace. Add any optional
image-source keys the same way. Runs are stored under the cloned repository's ignored `runs/`
folder; download important bundles before deleting the Codespace.

### Local Jupyter: maximum control

```bash
git clone https://github.com/FlashFeedLearningApp/knowledge-pack-studio.git
cd knowledge-pack-studio
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
jupyter lab notebooks/Knowledge_Pack_Studio_v2.ipynb
```

Set `OPENAI_API_KEY_FF_KP` in your environment for live runs. Mock runs need no credential.

## Native notebook flow

The notebook makes each major decision visible and leaves its artifact in the cell output:

1. Connect credentials and persistent checkpoint storage.
2. Enter an idea or resume a complete prior workspace.
3. Draft, answer, and explicitly approve the learning brief.
4. Run grounded web research and process supplied URLs/files.
5. Extract atomic claims with source support and instruction approval.
6. Plan lessons and parts before guide prose.
7. Write learner-facing guides from the approved plan and evidence.
8. Author items and run structural preflight before visual spending.
9. Plan visuals, then source first, generate explicitly, or skip.
10. Run deterministic validation, semantic review, and export.
11. Inspect the persisted activity log or download scrubbed diagnostics at any time.

Every stage prints live start/completion activity, agent/model identity, and available token/tool
usage. The same events remain in `run-manifest.json`, so losing a notebook connection does not lose
the run history.

## Source-first images

The recommended visual path uses the MIT-licensed
[Image Source-cery repository](https://github.com/garygeo-19/image-sourcery) at pinned revision
`5fc6ce4da1ca6ba869abc065a9495b5f6c92b73b`. It tries a ranked set of open or licensed providers
before optional generation and writes provider, source page, license, attribution, judge result,
checksum, and target item IDs into the image ledger.

Keyless providers include Wikimedia, iNaturalist, Library of Congress, Openverse, NASA, and The
Met. Unsplash, Pexels, and Smithsonian activate only when the author supplies their key. OpenAI
generation is never added as a fallback unless the notebook author explicitly enables it.

External-source metadata is provenance, not an automatic rights approval. The author must still
verify the source page, license, attribution, and suitability before community publication.

## Credential boundary

- Secrets are read into the active Python object and passed only to the selected provider.
- Secret values are never placed in configuration, artifacts, activity logs, diagnostics, exports,
  or notebook source.
- Mock mode is prominently identified, requires no key, and can never publish.
- Live image generation requires a separate confirmation argument.
- Public application hosting is not part of the standard architecture.

See [`SECURITY.md`](SECURITY.md) for the complete policy.

## Artifact layout

```text
runs/<run-id>/
  idea.json
  configuration.json
  run-manifest.json
  brief/
  research/
  evidence/
  design/
  guide/
  items/
  visuals/
  validation/
  publishable/<pack-id>/
  exports/<pack-id>-knowledge-pack-bundle.zip
```

The export separates consumer files from audit evidence and includes checksums. A failed or mock
run can still export a clearly marked `DRAFT` bundle for diagnosis and repair.

## Schema and requirements

The portable JSON Schema is included at [`schema/pack.schema.json`](schema/pack.schema.json). Its
provenance and authoritative upstream Zod links are in [`schema/README.md`](schema/README.md).
Pipeline schemas for the brief and evidence ledger are included beside it.

The complete, self-contained requirement is
[`docs/requirements/AUTOMATED_PIPELINE_REQUIREMENTS.md`](docs/requirements/AUTOMATED_PIPELINE_REQUIREMENTS.md),
with supporting reference documents vendored under [`docs/requirements/references/`](docs/requirements/references/).
See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for implemented versus planned scope.

## Development and verification

```bash
python -m pip install -e '.[dev]'
ruff format --check src tests scripts
ruff check src tests scripts
pytest
knowledge-pack-studio --smoke-run
```

The former browser prototype remains available only for comparison:

```bash
python -m pip install -e '.[legacy-ui]'
knowledge-pack-studio --legacy-ui
```

It is not the primary v0.2 experience and is not installed by the notebook runtime.

## Contributing and licensing

Community code and content contributions are welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md). Code and schema tooling are MIT licensed. Generated and
contributed learning content and every visual asset require their own explicit rights metadata.
