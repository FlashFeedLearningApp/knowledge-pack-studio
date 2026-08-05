# Contributing

Knowledge Pack Studio is intended to support open, community-authored learning content. Code,
content, and visual assets have different review and licensing needs.

## Development workflow

1. Create a focused branch from `main`.
2. Install with `python -m pip install -e '.[dev]'`.
3. Run `ruff format --check src tests`, `ruff check src tests`, and `pytest`.
4. Run `knowledge-pack-studio --smoke-run` for an end-to-end offline check.
5. Describe any schema, prompt, validation, credential, or rights impact in the pull request.

Do not commit API keys, requester documents, generated run folders, notebook outputs containing
secrets, or unlicensed media. Use synthetic or redistributable fixtures in tests.

## Contribution boundaries

- Schema changes require an upstream `@flashfeed/pack-schema` proposal; do not invent fields in a
  generated pack.
- Provider additions should implement the `PipelineProvider` protocol and preserve artifact and
  credential boundaries.
- Validation rules should use deterministic code where the decision can be expressed reliably.
- Prompt changes should include an evaluation case that demonstrates the intended improvement.
- Pack content needs an explicit content license; every external asset needs source and rights
  metadata.
- High-stakes topic support requires a documented human-review policy before release.

Read [`docs/requirements/AUTOMATED_PIPELINE_REQUIREMENTS.md`](docs/requirements/AUTOMATED_PIPELINE_REQUIREMENTS.md)
and [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) before making architectural changes.
