> **Note (standalone repo):** This is the canonical pack spec & standards, ported from
> the FlashFeed app repo. A few commands it references (`npm run dev`, the image-fetch
> scripts, `src/runtime/loader.ts` registration) belong to the private app and don't
> apply here — in this repo the flow is simply: author `packs/<id>.json`, then
> `npm run validate`. Everything about the data model, shapes, and content standards
> applies as written.

---

# Authoring Knowledge Packs

The canonical guide for creating FlashFeed knowledge packs. If you're generating
a new pack (by hand or with an LLM), this is the spec to follow. It is the source
of truth for the data model, the content↔interaction model, and the **standards**
every pack must meet (study guides, attribution, concepts).

> Companion docs: `SPEC.md` (product/runtime spec), `DEPLOY.md` (shipping),
> `ENGAGEMENT.md` (mechanics). Validate any pack with `npm run validate-packs`.

---

## 1. The big idea: content feeds *interactions*, not the other way around

A pack is just **content in typed shapes**. The runtime matches each game to the
shapes it accepts and schedules automatically — you never wire a pack to a game.
Add a `pair` and it instantly lights up Quiz Cards, Memory Flip, Word Scramble,
etc. So your only job is: **produce accurate content in the right shapes, and
group it into lessons.**

Three ways content gets made:
- **Reuse** — a shape you author lights up every compatible game for free.
- **Derive** (deterministic) — scripts turn existing shapes into new ones
  (`scripts/derive-content.mjs` → cloze + true/false from facts).
- **Author / generate** (LLM + judge) — genuinely new info: concept clues, short
  glosses, images. **Always fact-checked before shipping.**

Check coverage anytime with `npm run audit:matrix` (pack × game grid).

---

## 2. Files & layout

```
public/packs/<pack-id>.json                     # the pack
public/packs/guides/<pack-id>/<lesson-id>.md    # one study guide per lesson (REQUIRED)
public/packs/maps/<id>.png                      # generated map images (kind:"map")
public/packs/diagrams/<pack-id>/<id>.svg        # rendered diagrams (kind:"diagram")
public/packs/diagrams/<pack-id>/<id>.ir.json    # diagram-ir source (the durable artifact)
```

Register a new pack in `src/runtime/loader.ts` (`BUILTIN_PACKS`).

---

## 3. Pack structure

```jsonc
{
  "packId": "arizona-history",        // unique, kebab-case, matches filename
  "packName": "History of Arizona",   // full display name (≤80 chars)
  "shortName": "AZ History",          // ≤16 chars — shown on fact-card eyebrows
  "packVersion": "1.1",               // "N.N" or "N.N.N"
  "icon": "🌵",                       // 1–4 chars: emoji or initials
  "description": "…",                 // ≤400 chars
  "author": "Flash Feed",
  "language": "en",                   // pack language; gates language-specific games
  "items": [ /* every card, see §5 */ ],
  "lessons": [ /* curriculum, see §4 */ ]
}
```

`items` is the flat pool of cards. `lessons` organize them into a syllabus and
reference cards by id. An item id may appear in multiple parts (e.g. for review).

---

## 4. Lessons, parts & study guides

```jsonc
"lessons": [{
  "id": "l5-wild-west",
  "title": "The Wild West Era",
  "order": 5,
  "studyGuidePath": "/packs/guides/arizona-history/l5-wild-west.md",  // REQUIRED
  "sources": [ { "label": "…", "url": "…" } ],   // optional lesson-level provenance
  "parts": [{
    "id": "l5p2-ok-corral",
    "title": "Tombstone & the O.K. Corral",
    "order": 1,
    "blurb": "…",                  // optional one-liner on the splash
    "itemIds": ["fact-tombstone", "concept-wyatt-earp", "..."]
  }]
}]
```

- A **part** is the unit a game round is scoped to. The scheduler picks a part,
  then a compatible game, then draws items from it.
- Parts whose id contains `::` are **synthetic** (auto-derived buckets) and are
  hidden from the Library. Author ids never use `::`.

### ✅ STANDARD: every card must be traceable to a study guide
- **Every lesson MUST ship a study guide** (`studyGuidePath` → a real markdown
  file). Validation enforces the field; you must create the file.
- **Every card should live in an authored lesson/part**, so the runtime can
  surface its lesson's study guide (the in-feed Study button now resolves a
  standalone fact card → its lesson guide via the item→guide map).
- A card that belongs to no guided lesson has **no Study button** — treat that as
  a bug to fix by adding it to a lesson.
- The guide is prose that teaches the lesson; cards are the quiz layer over it.

### ✅ STANDARD: part-local quiz content (for "Lock It In")
- The **Lock It In** quiz after a fact carousel is scoped to that carousel's PART
  (see `LOCK_IT_IN.md`): it draws questions *first* from the same part's items, then
  tops up from the pack. So **author game-shaped items** (`mcq`, `pair`, `numeric`,
  `definition`, `concept`, `trueFalse`, `cloze`) **into the SAME part as the facts they
  reinforce** — a part == a study-guide section — not into a separate pack-wide or
  lesson-level pool.
- **Derived items** (`trueFalse`, `cloze` auto-generated by the pipeline) must attach
  to their **originating topical part**, not a synthetic lesson-level "derived bank"
  (a `::` part). Items pooled away from their facts can't scope to what was reviewed.
- Aim for **≥3–5 game-shaped items per part** so a Lock-it-in round is mostly in-scope.
  The audit (`scratchpad/measure.mjs` / content-matrix) flags **barren parts** (facts
  but no same-part game items) — fix those by authoring 3–5 items (prefer
  `pair`/`definition`/`numeric`) derived from that part's facts.

### The mastery layer: objectives, demonstrations & Objective Tests

Beyond the raw "cards over a guide," a lesson can declare **what a learner should be
able to do** and **how they prove it**. This is optional and back-compatible (a lesson
without it uses the legacy "answered enough correctly" completion count), but it's the
standard for new packs. Three nested fields on a `Lesson` (all validated by
`@flashfeed/pack-schema`):

```jsonc
"lessons": [{
  "id": "l2-cardiovascular",
  "studyGuidePath": "…",
  "parts": [ … ],

  // 1. LEARNING OBJECTIVES — concrete, demonstrable outcomes. Lesson completion =
  //    every objective demonstrated. `statement` ≤160 chars, starts with a verb.
  "objectives": [
    { "id": "obj-cv-acs", "statement": "Recognize acute coronary syndrome, its biomarkers, and STEMI criteria", "demonstrationIds": ["d-acs-concept", "d-acs-markers"] }
  ],

  // 2. DEMONSTRATIONS — bundles of pack items that, answered correctly, evidence an
  //    objective. Many-to-many: one demo can serve several objectives. `requiredCorrect`
  //    defaults to all items. This is the FALLBACK proof when an objective has no test.
  "demonstrations": [
    { "id": "d-acs-concept", "itemIds": ["cz-…-acs", "cv-mcq-stemi-criteria"], "requiredCorrect": 1 },
    { "id": "d-acs-markers", "itemIds": ["cv-def-troponin", "cv-num-door-balloon"] }
  ],

  // 3. OBJECTIVE TESTS — a focused MCQ EXAM that proves an objective (the accountable
  //    path; preferred over scattered demonstrations). See the rules below.
  "objectiveTests": [
    { "id": "test-cv-acs", "objectiveId": "obj-cv-acs", "title": "Acute Coronary Syndrome",
      "mcqIds": ["mcq-…-acs", "cv-mcq-troponin-marker", "cv-mcq-inferior-mi", "cv-mcq-stemi-criteria", "cv-mcq-reperfusion-strategy"] }
  ]
}]
```

#### ✅ STANDARD: Objective Tests (the exam layer)

An **Objective Test** is a single MCQ exam that a learner takes to prove ONE objective.
Passing it (**~80% correct, retryable**) marks the objective met — the study guide shows
"Take the test ›" and the objective checks off. Rules the schema + tooling enforce:

- **5–10 questions.** ~5 for a focused objective, up to 10 for a broad one. An objective
  may carry **1–2 tests** (a second only when it spans a lot of distinct content).
- **`mcqIds` are `mcq` items in THIS pack.** **Reuse existing MCQs first** (so a learner
  recognises questions from the feed), then **generate new ones** to fill the gap. Give
  generated questions ids prefixed `ot-` (namespaces them from hand-authored items).
- **`id` is unique across the whole pack** (it keys the learner's pass record).
  **`objectiveId`** must resolve to an objective **in the same lesson**.
- **Question quality bar** (same as any MCQ, §5 `mcq`): exactly 4 options, one
  unambiguously correct, three plausible-but-clearly-wrong distractors from the same
  category; factually accurate to the guide; **no answer leak** (never name the answer in
  the prompt); a ≤300-char explanation; vary styles (recall / "which is NOT" / apply).
- **⚠ Options must survive de-duplication.** The app drops near-duplicate options at
  render (`@flashfeed/core` `dedupeOptions`): plurals, possessives, and **whole-word
  containment** — where one option's words are a run of another's after punctuation,
  operators (`× ÷ + −`), and arrows (`↑ ↓`) are stripped. So `M × A × P` vs `M + A + P`,
  `↓CVP` vs `↑CVP`, and `943 ft` vs `1,943 ft` all collapse to a 3-option question. Write
  distractors that differ in **words** (spell out formulas; use "high/low" not arrows;
  avoid one number being a prefix of another). The validator rejects collisions.

#### How Objective Tests are produced

Author by hand in `lesson.objectiveTests`, or use the **deriver** (recommended at scale),
in `flashfeed-knowledge-packs`:

```bash
node scripts/objective-tests-context.mjs <pack>      # per-lesson guide + reusable MCQs + item facts
# author + skeptic-verify one test per objective (reuse-first, generate the rest):
#   Workflow tools/author-objective-tests.wf.js  args { root, work:[{packId,lessonId}] }
node scripts/objective-tests-validate.mjs <pack>     # 5–10 resolve · mcq-shape · no leak · no dedupe collision
node scripts/objective-tests-compile.mjs             # merge generated ot-* MCQs into pack.json (+ prune superseded)
node scripts/objective-tests-fold.mjs --bump <pack>  # (after schema ≥0.3.0) write lesson.objectiveTests into pack.json
```

The nightly QA judge `tools/judge-objective-tests.wf.js` re-checks every exam question
(keyed answer correct, fair distractors, no leak, on-objective). Objectives + tests are
**LLM-derived from the study guide, then reviewed** — the guide is the source of truth,
so a thorough guide yields good exams.

---

## 5. Item shapes (cards)

Every item has: `id`, `tags: string[]`, optional `illustration`, optional
`source` (§7), plus shape-specific fields. One item = one **card** = one screen.

| shape | key fields | feeds (main games) |
|---|---|---|
| `fact` | `title` (≤80), `body` (≤600), `factVariant?` (`image-heavy`→hero / `scrapbook`), `imageCaption?` | feed cards (carousel / hero / scrapbook / map) |
| `pair` | `sideA`, `sideB` (Slots; `sideB.short?` for MCQ options) | Quiz Cards, Lightning Round, Memory Flip, Word Hunter, Word Scramble, Word Search, NPC Dialogue, Whack Word, Sort the Pile, Trivia Bet, Highway Hunt |
| `definition` | `term`, `definition` (Slots) | Term Drill, Word Hunter, Word Scramble, Sort the Pile |
| `mcq` | `prompt`, `options[2–4]`, `correctIndex`, `explanation?` | Quiz Cards, Lightning Round, Trivia Bet |
| `numeric` | `prompt`, `value` (number), `unit?`, `tolerance?` | Higher or Lower, The Estimator, Magnitude Stack |
| `cloze` | `template` (use `___` — exactly 3 underscores — to mark the blank), `answer`, `distractors[1–4]` | Fill the Blank |
> **Cloze rule:** the blanked `answer` MUST be a **key concept or proper noun** — a
> term, name, place, book, framework, or number — **never** an article,
> preposition, pronoun, auxiliary, or generic verb/adverb ("the", "a", "when",
> "buy"). The auto-deriver enforces this (it only blanks a multi-word proper noun,
> a year, or a single word the pack *teaches* as a term); `scripts/cloze-quality.test.ts`
> fails the build on a filler blank. Hand-authored exception: a deliberate
> pick-the-value drill whose distractors are the same category (the **two** natures
> of Christ with `one/three/four`).
| `trueFalse` | `statement`, `isTrue`, `why`, `whyOptions?`, `whyCorrectIndex?` | True or False, Right or Wrong |
| `comparison` | `prompt`, `correct`/`incorrect` (each a side w/ `caption` + optional image) | Right or Wrong |
| `sentence` | `tokens[]`, `correctOrder[]`, `translation?` | Word Scramble (sentence) |
| `video` | `videoId`, `title`, `startSec?`, `endSec?`, `pollMarks?` | Watch & Catch |
| `procedure` | `goal`, `steps[2–10]`, `notes?` | Sequence It, Snake |
| `concept` | `conceptKind`, `name`, `clues[2–4]` | Who / Where / What / When Is It? (§6) |

A **Slot** is `{ modality: "text"|"image"|"audio", value, alt?, short? }`. Image/
audio slots require `alt`. `short` (≤60) is a compact answer form for MCQ options.

**Numeric `unit`** matters: it sets formatting (`year` → `1853`, not `1,853 year`)
and **comparability**. Numeric games group by physical dimension *and magnitude*,
so a 30-inch fish never compares to a 20-mile drive. Always set a real `unit`.

Minimal `fact`:
```jsonc
{ "id": "fact-saguaro", "shape": "fact", "tags": ["flora"],
  "title": "The Saguaro", "body": "A giant cactus of the Sonoran Desert…",
  "illustration": { "kind": "photo", "imagePrompt": "…", "imageSearchTerm": "saguaro cactus", "alt": "A saguaro" } }
```

---

## 6. Key concepts — `concept` shape + the "Is It?" games

A **key concept** is a person, place, thing, or event worth recognizing, with
progressive clues. It powers four guessing games (one per kind):
**Who Is It?** (person), **Where Is It?** (place), **What Is It?** (thing),
**When Is It?** (event).

```jsonc
{
  "id": "concept-geronimo",
  "shape": "concept",
  "conceptKind": "person",        // "person" | "place" | "thing" | "event"
  "tags": ["key-concept", "person"],
  "name": "Geronimo",             // the answer + the option label (≤80)
  "clues": [                      // 2–4 clues, BROAD → SPECIFIC, ≤200 each
    "An Apache leader who fought to defend his homeland in the late 1800s.",
    "He evaded thousands of U.S. and Mexican troops for years.",
    "His 1886 surrender in Skeleton Canyon ended the major Apache Wars."
  ]
}
```

**`conceptKind` definitions (use exactly these — the model drifts otherwise):**
- **person** — a real individual (historical or living). Not a place/object/group.
- **place** — a *geographic* location: city, country, region, or natural feature
  (mountain, desert, river, ocean, canyon, island). **Not** a building/structure.
- **thing** — an object, man-made structure, product, material, species, or
  concept (bridge, tower, planet, crop, animal). Not a person and not a place.
- **event** — a specific historical or notable event/happening (battle, treaty,
  founding, disaster, discovery, election, movement), anchored to a date or
  period. Not a person, place, or object.

**Authoring rules**
1. **Group ≥6 same-kind concepts in one part** (the game shows 1 target + 5
   distractors). The game's `partFilter` won't schedule it otherwise.
2. **Never name the answer (or an obvious cognate) inside a clue.**
3. **Clue 1 broad, clue 3 most identifying.** Each clue must be **accurate** —
   a wrong clue actively mis-teaches.
4. Make the set **plausibly confusable** (same category), so deduction is fun.
5. Put them in a "Key Concepts" lesson with parts `Key People / Places / Things`.

**Pipeline (`scripts/derive-concepts.mjs`)** — draft → judge → promote:
```bash
# 1. draft → writes a review sidecar <pack>.concepts-draft.json (gitignored)
node scripts/derive-concepts.mjs --n=6 --kinds=place,thing public/packs/<pack>.json
# 2. FACT-CHECK and edit the sidecar JSON (fix or cut clues)
# 3. promote → writes the EXACT judged draft into the pack (no LLM call)
node scripts/derive-concepts.mjs --promote public/packs/<pack>.json
```
Judging is mandatory: real catches so far include a Shanghai-Tower height error
and an LLM clue crediting Bengio with LSTMs. Not every pack fits every kind — a
vocab pack has no "people"; skip combos that don't make sense.

---

## 7. Attribution & provenance — at the card/image level, not the pack level

> **Standard:** pack-level attribution alone is **not** sufficient. Image
> attribution lives **on the image**; content attribution lives **on the card**
> (lesson-level is an acceptable fallback).

### Images — `illustration.credit` + `illustration.creditUrl`
```jsonc
"illustration": {
  "kind": "photo",
  "url": "https://images.unsplash.com/photo-…",
  "imagePrompt": "…",            // authoring hint, never shown
  "imageSearchTerm": "saguaro cactus",
  "alt": "A saguaro cactus",     // REQUIRED accessibility fallback
  "credit": "Unsplash · Jane Doe",
  "creditUrl": "https://unsplash.com/photos/abc123"   // link to the ORIGINAL photo
}
```
- `credit` (text) **and** `creditUrl` (link to the source photo page) are now set
  automatically by `scripts/fetch-images.ts` for Unsplash. **Always keep the
  source link** — providers' terms require attribution that links back.
- **Judge every fetched image** before committing — Unsplash text-matches but is
  ~80% on-subject (it returned a great white for "mako", Saturn for "Jupiter",
  a Hyundai Tucson for "peppers for Tucson"). Cut wrong-subject images; revert to
  text-only rather than ship a misleading photo. Subject-specific search terms
  beat templated ones ("tomato hornworm caterpillar", not "<x> Arizona garden").
- `kind`: `"photo"` (stock fetch) · `"diagram"` / `"map"` / `"chart"` (committed
  asset, fetch skips it).

### Content — item `source`, or lesson `sources`
```jsonc
// preferred: per-card
{ "id": "fact-gadsden", "shape": "fact", "title": "…", "body": "…",
  "source": { "label": "Perplexity research doc — AZ borders", "url": "…" } }

// acceptable fallback: whole-lesson
"lessons": [{ "id": "l3-treaties", "studyGuidePath": "…", "sources": [
  { "label": "Treaty of Guadalupe Hidalgo (1848), Library of Congress", "url": "…" }
]}]
```
Use card-level `source` where cards differ; lesson `sources` when a whole lesson
shares one. The Sources screen lists these (the image-source links and per-item
content sources are the path off broad pack-level attribution).

---

## 8. Validation, audits & scripts

```bash
npm run validate-packs        # schema-validate every pack (run before commit)
npm run audit:matrix          # pack × game coverage grid
npm run audit-coverage        # deeper content coverage audit

# content generation (all LLM steps require fact-checking)
node scripts/derive-content.mjs <pack>          # cloze + true/false from facts (deterministic)
node scripts/derive-concepts.mjs … <pack>       # concepts (draft→judge→promote, §6)
npm run derive-short-forms -- <pack>            # concise sideB.short MCQ glosses (LLM)
node scripts/fetch-images.ts <pack> [--providers unsplash]   # images (judge results!)
node scripts/generate-maps.mjs [--force]        # render map cards (kind:"map")
```

In-app: **Library (★) → 📊 Coverage** shows, per pack, how many cards have
appeared on screen and how many are never surfacing (per device).

---

## 9. Authoring checklist (definition of done for a new pack)

- [ ] `packId` matches filename; `packName`, `shortName` (≤16), `icon`, `language` set.
- [ ] Every item has a real `unit` if `numeric`; image slots have `alt`.
- [ ] Content grouped into **lessons → parts**; every lesson has a **study guide file**.
- [ ] Every card is reachable from a guided lesson (no orphan cards).
- [ ] **Learning objectives** per lesson (verb-led, ≤160 chars) + **demonstrations** that prove them (item ids resolve).
- [ ] **Objective Tests**: one MCQ exam per objective — 5–10 questions, reuse-first + generated `ot-*` for gaps, options that **survive dedup** (no operator/arrow/contained twins), no answer leak, **judged**. `objective-tests-validate` passes.
- [ ] Concepts: ≥6 same-kind per part, 2–4 broad→specific clues, never name the answer, **fact-checked**.
- [ ] Images: `kind` set; `credit` + `creditUrl` present; **every image judged** for subject accuracy.
- [ ] Diagrams: a **few per pack** (more for timeline/sequence/procedure-heavy packs), authored as `diagram-ir` IR in the **Excalidraw theme** (`excalight`/`excalidark`), `.ir.json` + `.svg` committed, rendered SVG judged. See `AUTHORING.md → Structured diagrams with diagram-ir`.
- [ ] Provenance: card-level `source` (or lesson `sources`) for non-obvious content.
- [ ] `npm run validate-packs` passes; pack registered in `loader.ts`.

---

## 10. To be formalized / open questions

These are known gaps — capture decisions here as they're made:

- **Sources-screen UI for the new fields.** `creditUrl` and item/lesson `source`
  are now in the schema and populated for images, but the Sources screen still
  renders provider-grouped attribution; it should render per-image links and
  per-card content sources.
- **Backfill `creditUrl` for already-fetched images.** Existing illustrations
  have `credit` but no `creditUrl` (added after they were fetched). A re-fetch
  with `--force` or a small backfill script would fill them.
- **Content `source` is not yet populated** on existing packs — only the schema
  exists. New packs should author it from the start; old packs need a pass.
- **Mandatory vs. optional.** Today study guides are required, but `source`/
  `creditUrl` are optional. Decide if/when to make provenance required in
  validation (e.g. "every image must have `creditUrl`").
- **Per-item study-guide anchors.** Parts can set `studyGuideAnchor`; cards could
  deep-link into the exact guide section rather than the lesson top.
