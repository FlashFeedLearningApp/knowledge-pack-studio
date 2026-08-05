# Schema provenance

`pack.schema.json` is the portable Draft 2020-12 representation of the FlashFeed consumer schema.

- Included schema version: `0.3.0`
- Pack schema source package: [`@flashfeed/pack-schema`](https://www.npmjs.com/package/@flashfeed/pack-schema)
- Declared schema source: <https://github.com/Recurxive/flashfeed-serving/tree/main/packages/pack-schema>
- Knowledge-pack repository: <https://github.com/FlashFeedLearningApp/knowledge-packs>
- Standalone definition source: <https://github.com/FlashFeedLearningApp/knowledge-packs/tree/main/pipeline-definition>
- Original copied-file SHA-256: `7138d6ec4ce84679376e22b830bf8d4267815aea722210feec52f8cb22355413`

The upstream Zod schema is authoritative. This JSON Schema covers portable structural validation;
application validators must additionally check uniqueness, item references, part assignments,
answer indices, files, provenance, and semantic quality.

The other `*.schema.json` files are generated from the application's strict Pydantic artifact
models and cover the approved brief, research dossier, evidence ledger, curriculum/pack design,
authored items, visual plan, validation report, semantic review, and resumable run manifest.
Regenerate them with `python scripts/export_pipeline_schemas.py`.
