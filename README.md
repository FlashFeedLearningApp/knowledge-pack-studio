# Knowledge Pack Studio

Knowledge Pack Studio is a Colab-first, evidence-led authoring pipeline for FlashFeed knowledge
packs. It turns an idea into an approved brief, grounded research dossier, claim-level evidence
ledger, study guide, pack design, authored items, optional generated visuals, validation report,
semantic review, and a portable ZIP bundle.

The application is intentionally local-first: each author runs it in their own Colab runtime and
supplies their own OpenAI API key. No shared hosted service or maintainer-funded model usage is
required.

> **Development status:** Milestone 1 vertical slice. Mock mode is fully offline and deliberately
> fails the publication gate. Live OpenAI integration is implemented but requires the user's key
> and should be evaluated on representative topics before release.

## Open in Colab

[![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/github/FlashFeedLearningApp/knowledge-pack-studio/blob/main/notebooks/Knowledge_Pack_Studio.ipynb)

The notebook is [`notebooks/Knowledge_Pack_Studio.ipynb`](notebooks/Knowledge_Pack_Studio.ipynb).

The governing requirement is included in full at
[`docs/requirements/AUTOMATED_PIPELINE_REQUIREMENTS.md`](docs/requirements/AUTOMATED_PIPELINE_REQUIREMENTS.md),
with its supporting authoring references vendored beside it. See
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the implemented milestone and explicit gaps.

## What the first vertical slice does

1. Preserves the original idea.
2. Drafts a clarification brief without auto-approving it.
3. Pauses for explicit requester approval.
4. Runs OpenAI Responses API web search and accepts requester files.
5. Extracts an evidence ledger with claim-to-source support.
6. Writes a study guide using only approved claims.
7. Creates a lesson, part, shape, and ratio plan.
8. Authors supported FlashFeed seed shapes.
9. Plans and optionally generates instructional images.
10. Validates against the pinned FlashFeed JSON Schema and deterministic gates.
11. Runs a logically separate semantic review.
12. Exports a consumer pack plus an audit folder and checksums.

The Gradio Studio also restores all persisted artifacts when a run is resumed, offers an optional
"I'm Feeling Lucky" path with explicit automatic-stage and auto-approval controls, and can download
a credential-scrubbed session diagnostics bundle after a failure. Image generation remains an
independent opt-in because it adds cost and is not required for every learning objective.

## Local development

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -e '.[dev]'
knowledge-pack-studio --smoke-run
pytest
knowledge-pack-studio
```

Mock mode does not need an API key. For live Colab use, add `OPENAI_API_KEY_FF_KP` to Colab Secrets.
The notebook intentionally does not fall back to a generic OpenAI secret, which helps authors with
multiple keys select the Knowledge Pack credential explicitly. The Studio has no API-key input: it
only reports whether the dedicated credential was connected when the app launched. For local use,
set the environment variable `OPENAI_API_KEY_FF_KP` before launching the CLI. Also add
`FF_KP_STUDIO_PASSWORD`; the temporary Gradio share link uses the username `ff-kp-author` and that
password. Keys and passwords are never written into run artifacts or export bundles.

## Artifact layout

Each run is checkpointed after every stage:

```text
runs/<run-id>/
  run-manifest.json
  brief/
  research/
  evidence/
  guide/
  design/
  items/
  visuals/
  validation/
  publishable/<pack-id>/
  exports/<pack-id>-knowledge-pack-bundle.zip
```

The bundle separates the runtime-facing pack from authoring evidence:

```text
publishable/<pack-id>/
  pack.json
  guides/study-guide.md
  generated/
audit/
  schema/pack.schema.json
  research-dossier.json
  evidence-ledger.json
  validation-report.json
  semantic-review.json
  run-manifest.json
SHA256SUMS
```

## Schema contract

The canonical portable schema is [`schema/pack.schema.json`](schema/pack.schema.json), copied from
the FlashFeed pipeline-definition package at version `0.3.0`. Its provenance and authoritative Zod
source links are recorded in [`schema/README.md`](schema/README.md).

JSON Schema is the portable first pass. The upstream Zod validator remains authoritative for
cross-array and referential rules that JSON Schema cannot fully express. A future GitHub Actions
release gate will run both.

## Safety and quality policy

- Failures remain failures; there are no canned passing reports.
- Mock runs cannot be published.
- Generated images are illustrations, not factual evidence.
- No image receives invented licensing or source credits.
- Every authored item must trace to an approved claim.
- The deterministic orchestrator—not an unconstrained LLM—controls stage order and approvals.
- High-stakes topics require human review and are not autonomously publishable.

See [`SECURITY.md`](SECURITY.md) for credential handling.

## Contributing

Community code and content contributions are welcome. Start with
[`CONTRIBUTING.md`](CONTRIBUTING.md); pack content and visual assets require explicit licensing and
provenance in addition to code review.

## Licensing

Code and schema tooling are licensed under MIT. Generated and contributed learning content requires
its own explicit license and per-asset rights metadata before community publication.
