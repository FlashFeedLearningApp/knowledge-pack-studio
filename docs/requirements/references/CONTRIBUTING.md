# Contributing

Thanks for helping build FlashFeed's open knowledge packs. This guide covers how to add or improve a pack and the standards a pack must meet.

## The flow

1. **Fork** and branch.
2. **Author** your pack as a self-contained folder `packs/<pack-id>/` (copy a [template from the source repository](https://github.com/FlashFeedLearningApp/knowledge-packs/tree/main/templates) into it as `pack.json`; put its study guides in `guides/`, images in `images/`). Keep one pack to one subject.
3. **Validate:** `npm install` then `npm run validate packs/<pack-id>/pack.json`. It must print `OK` (CI runs the same check on every PR).
4. **Open a PR.** Describe the subject, the number of items, and the lessons/parts.

## The essentials

Read [`KNOWLEDGE_PACKS.md`](KNOWLEDGE_PACKS.md) (the canonical spec) and [`SHAPES.md`](SHAPES.md) (per-shape JSON). The high points:

- **One pack = one subject.** Mixing unrelated domains breaks the game round-scoping.
- **Parts are 6–10 items** of one coherent topic. A part is the unit a review round is scoped to, so keep it cohesive. Smaller parts lock out half the games.
- **Part-local quiz content.** Author game-shaped items (`mcq`, `pair`, `numeric`, `definition`, `concept`, `trueFalse`, `cloze`) *into the same part as the facts they reinforce* — a review round draws from what was just read (aim for ≥3–5 game items per part). See the "part-local quiz content" standard in the spec.
- **Item ids are unique** within a pack; use `prefix-slug` style (`pair-aeropuerto`, `mcq-cuenta`).
- **Tags drive grouping** — 2–4 per item, broad→specific; the first tag matters most.
- **Every card should trace to a study guide.** Each lesson/part ships a real study-guide `.md` under `packs/<pack-id>/guides/`.

## Content you have the right to share

Everything you submit is published under the repo's licenses (code MIT, content CC BY 4.0), so:

- **Write original text**, or paraphrase from sources and cite them (`source` on the item, or `sources` on the lesson). Don't paste copyrighted passages.
- **Images must be redistributable** — your own work, public domain, or a Creative Commons / equivalently-licensed image with attribution recorded in `illustration.credit` + `creditUrl`. **Do not** submit scraped photos, press images, or portraits of people whose rights you don't hold. When in doubt, ship text-only — the app renders gracefully without an image.
- See [PROVENANCE.md](PROVENANCE.md) for how image provenance is tracked.

## Attribution & accuracy

- **Accuracy is the bar.** Facts must be correct; clues must never name their own answer; numeric items need a real `unit`. Bad content is worse than no content.
- **Attribution lives on the item:** content provenance in `source`, image credit in `illustration.credit`/`creditUrl`. Pack-level attribution alone isn't enough.

Questions or a shape that doesn't fit the schema? Open an issue before authoring — don't invent a new shape.
