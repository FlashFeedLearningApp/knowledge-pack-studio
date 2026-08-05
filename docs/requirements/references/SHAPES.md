# Content Shape Reference

Every item in a pack has a `shape` field that determines its structure. **Ten live shapes** (`video` and `sentence` were dropped 2026-07-08 — see below). Pick the one that matches the cognitive task you're trying to teach. New here? Read the **Shape Standard** section first for the authoring bar.

> Canonical spec: **[`KNOWLEDGE_PACKS.md`](KNOWLEDGE_PACKS.md)**. This file is the
> per-shape JSON-example companion; if they disagree, the canonical spec and
> `src/content/schema.ts` win.

All shapes share these base fields:

```jsonc
{
  "id": "unique-within-pack",     // required, unique (globally unique across ALL packs)
  "tags": ["..."],                 // 1-4 tags; first one is the grouping bin
  "linkedItemIds": ["..."],        // optional cross-references (e.g. fact → recall)
  "illustration": { ... },         // optional supporting image (see end)
  "source": {                      // optional content provenance for THIS card (see §7 of canonical spec)
    "label": "Perplexity research doc — AZ borders",
    "url": "https://…"             // optional
  }
}
```

---

## Shape Standard — the authoring bar

The bar a good pack meets (measured by the audit — see **[AUDIT.md](AUDIT.md)**).

**Ten live shapes.** `video` and `sentence` were **dropped** (2026-07-08; removed
from `schema.ts`). Author against: `fact`, `pair`, `definition`, `numeric`,
`concept`, `mcq`, `procedure`, `comparison` — plus the two **derived** skins
`trueFalse` and `cloze`, which you **never hand-author** (the deriver harvests
them from your fact/pair/definition seeds).

**Three principles:**
1. **Coverage-first.** A good pack covers all ten live shapes, anchored by an
   authored substrate (fact + pair + definition + numeric + concept + at least one
   authored `mcq` per section, plus procedure/comparison where the topic supports).
2. **Part-coherent.** Everything resolves through the **part** (= one study-guide
   `<h2>` section): its carousel facts, its seed items, and the derived quiz all
   belong to that part, so a "Lock It In" round quizzes ~90% on what was just
   reviewed. Don't group items by shape into pack-wide banks.
3. **Derived skins are capped, never the plurality.** `trueFalse` and `cloze` are
   machine-harvested by the deriver. `trueFalse` is capped at **≤ ⅓ of a part**
   (~1 per seed); if T/F is a pack's plurality, the fix is to *grow the other
   shapes*, not cut T/F. `cloze` derives from definitions (recall: blank the term)
   and facts (blank a proper noun) — so richer definitions ⇒ richer cloze.

**Target profile per pack** (priority · rough target):
- `fact` core · 12–20%, ≥3/part · `pair` core · 10–20% · `definition` strong · 5–12%
- `numeric` strong · 5–12%, ≥6 comparable-unit per cluster · `mcq` strong · ≥1
  **authored** per part · `concept` strong · confusable **same-`conceptKind`** sets
  per lesson · `procedure`/`comparison` supporting · where a real sequence / A-vs-B exists
- `trueFalse` derived, **capped ≤⅓** · `cloze` derived

**Images:** every photo carries a `credit` (+ `creditUrl`); stock-first
(Pexels/Unsplash/Wikimedia/Openverse), AI generation only as a fallback; no image
reused across cards. See **[PROVENANCE.md](PROVENANCE.md)**.

---

## `pair` — paired vocab / matching

Symmetric paired content. Drives Memory Flip, Audio Catch, Word Search, Quiz Cards (as derived MCQ), Sort the Pile.

```json
{
  "id": "pair-aeropuerto",
  "shape": "pair",
  "sideA": { "modality": "text", "value": "aeropuerto" },
  "sideB": { "modality": "text", "value": "airport" },
  "tags": ["transportation", "aeropuerto"]
}
```

Modalities: `"text"`, `"image"`, `"audio"`. Most packs use text↔text. Audio Catch uses text↔text but speaks `sideA` via TTS.

---

## `mcq` — multiple choice

Explicit question + 2–4 options. Drives Quiz Cards, NPC Dialogue, Space Invaders, Breakout.

```json
{
  "id": "mcq-aeropuerto",
  "shape": "mcq",
  "prompt": { "modality": "text", "value": "What does 'aeropuerto' mean?" },
  "options": [
    { "modality": "text", "value": "airport" },
    { "modality": "text", "value": "train station" },
    { "modality": "text", "value": "hotel" },
    { "modality": "text", "value": "bus stop" }
  ],
  "correctIndex": 0,
  "explanation": "Aeropuerto literally means 'air port' — where planes land and take off.",
  "tags": ["transportation"]
}
```

`correctIndex` is 0-based. `explanation` is shown after the player answers (in games that surface it).

---

## `definition` — term + meaning

Asymmetric: quizzing the term → its definition. (For "what term has this meaning?" use `pair`.)

```json
{
  "id": "def-tren",
  "shape": "definition",
  "term": { "modality": "text", "value": "tren" },
  "definition": { "modality": "text", "value": "A long vehicle that runs on rails and carries passengers or cargo." },
  "tags": ["transportation"]
}
```

---

## `numeric` — magnitudes, dates, quantities

Drives Higher or Lower and The Estimator. **Items in the same Part must share comparable units** (don't mix populations with heights — the round-builders will skip mixed parts).

```json
{
  "id": "pop-tokyo",
  "shape": "numeric",
  "prompt": { "modality": "text", "value": "Population of Tokyo metro area" },
  "value": 37340000,
  "unit": "people",
  "tags": ["population"]
}
```

`tolerance` is optional and used by the Estimator's accuracy scoring.

---

## `fact` — pure exposition

No recall. Used as feed interstitials and as "teach before test" linked prompts.

```json
{
  "id": "fact-aeropuerto",
  "shape": "fact",
  "title": "Aeropuerto",
  "body": "**Aeropuerto** means *airport*. It comes from *aero* (air) + *puerto* (port) — literally an 'air port'.",
  "tags": ["transportation", "vocabulary"]
}
```

`body` is markdown — supports `**bold**`, `*italic*`, paragraph breaks. Keep it concise.

When you want a fact to appear right before its related recall item, both the fact and the item should share at least one **tag** OR you can add the fact's id to the item's `linkedItemIds`.

### Fact variants — how a fact renders in the feed

A `fact` renders as one of three card types (see `src/runtime/factTypes.ts`):

- **carousel** (default) — a normal text card; if it has an image, the image is secondary.
- **hero** — a big, image-forward card. A fact becomes a hero when it **has an
  image** AND is either `factVariant: "image-heavy"` OR a photo with a short
  `body` (≤80 chars). Give a hero fact a punchy **`imageCaption`** (≤160 chars) —
  that's the overlay text. Hero facts light up the **Hero Facts** feed type. Curate
  them: pick striking, visually-sourceable facts, give each a great image, and set
  `factVariant: "image-heavy"` + an `imageCaption`.
- **scrapbook** — `factVariant: "scrapbook"` + `illustration.kind: "scrapbook"`: an
  AI-generated, image-only "topic overview" poster (collage/journal style, text baked
  into the image). Don't hand-author these — generate them with
  `npm run gen-scrapbooks` (drafts on-theme prompts from the pack's metadata, renders
  with gpt-image-1 to `public/packs/generated/<pack>/scrapbook-N.webp`, and injects the
  items). Always `--dry-run` first to eyeball prompts, then view the WebPs and judge for
  theme/lettering before committing. They're excluded from `cardCount` (cosmetic novelty).

`map` is a fourth render path (`illustration.kind: "map"`). All variants are optional.

---

## `concept` — a person / place / thing to recognize from clues

Drives **Who Is It?** (person), **Where Is It?** (place), **What Is It?** (thing) — one game per `conceptKind`. The game shows 2–4 progressive clues (broad → specific) and 6 options; the player names the target.

```json
{
  "id": "concept-geronimo",
  "shape": "concept",
  "conceptKind": "person",
  "tags": ["key-concept", "person"],
  "name": "Geronimo",
  "clues": [
    "An Apache leader who fought to defend his homeland in the late 1800s.",
    "He evaded thousands of U.S. and Mexican troops for years.",
    "His 1886 surrender in Skeleton Canyon ended the major Apache Wars."
  ]
}
```

- `conceptKind`: `"person"` | `"place"` (geographic — city/region/natural feature, **not** a building) | `"thing"` (object, structure, species, product, concept).
- `name`: the answer + the option label (≤80).
- `clues`: **2–4**, ≤200 each, ordered **broad → specific**. **Never name the answer (or an obvious cognate) inside a clue.** Every clue must be accurate — a wrong clue mis-teaches.
- **Group ≥6 same-kind concepts in one part** or the game won't schedule it (1 target + 5 distractors). Make the set plausibly confusable (same category).

**Authoring pipeline** — `scripts/derive-concepts.mjs` (draft → judge → promote):
```bash
node scripts/derive-concepts.mjs --n=6 --kinds=place,thing public/packs/<pack>.json   # writes a review sidecar
# FACT-CHECK and edit the sidecar JSON (fix or cut clues) — judging is mandatory
node scripts/derive-concepts.mjs --promote public/packs/<pack>.json                    # writes judged draft into the pack
```
See [`KNOWLEDGE_PACKS.md`](KNOWLEDGE_PACKS.md) §6 for the full standard.

---

## `video` — YouTube clip with optional polls

> **⚠ DROPPED (2026-07-08).** Removed from `schema.ts`; do not author. Retained
> here for historical reference only. (Reliance on third-party clips + a single
> consuming game made it low-value.)

Drives Watch & Catch. Embeds a YouTube video and can pause at specific timestamps to ask a question.

```json
{
  "id": "video-zoo",
  "shape": "video",
  "provider": "youtube",
  "videoId": "jNQXAC9IVRw",
  "startSec": 0,
  "endSec": 19,
  "title": "The first YouTube video, ever",
  "credit": "Jawed Karim, April 2005",
  "tags": ["video", "history"],
  "pollMarks": [
    {
      "atSec": 5,
      "prompt": "Where is the speaker standing?",
      "options": ["At an elephant exhibit", "In a forest", "At a museum"],
      "correctIndex": 0,
      "explanation": "He's at the San Diego Zoo."
    }
  ]
}
```

`atSec` values are relative to the clip start (so if `startSec` is 10 and `atSec` is 5, the poll fires at the video's 15-second mark).

---

## `procedure` — ordered steps

Drives Sequence It. A goal + the canonical order of steps. The game shuffles them at round time.

```json
{
  "id": "proc-light-switch",
  "shape": "procedure",
  "goal": "Wire a simple single-pole light switch",
  "steps": [
    "Turn off the breaker for the circuit and verify with a tester.",
    "Connect the incoming hot wire to one of the switch's brass screws.",
    "Connect the wire going to the light fixture to the other brass screw.",
    "Pigtail the neutrals (white wires) together — they bypass the switch.",
    "Bond the bare copper grounds to the green ground screw on the switch."
  ],
  "notes": "Neutrals NEVER go through the switch.",
  "tags": ["electrical", "wiring"]
}
```

5–8 steps is the sweet spot. `notes` is shown after the player solves.

---

## `cloze` — fill in the blank

Drives Fill the Blank. Template uses `___` (three underscores) to mark the blank.

```json
{
  "id": "cloze-usestate",
  "shape": "cloze",
  "template": "React's ___ hook stores a piece of component-local state that triggers a re-render when updated.",
  "answer": "useState",
  "distractors": ["useEffect", "useRef", "useMemo"],
  "explanation": "useEffect is for side effects, useRef holds a value without re-rendering, useMemo caches a computed value.",
  "tags": ["react", "code"]
}
```

`distractors` are the wrong options shown alongside `answer`. 2–3 distractors is right.

> **The blank must be a KEY CONCEPT or PROPER NOUN — never filler.** A
> fill-in-the-blank earns its keep only when the blanked word is the thing worth
> knowing: a term, name, place, book, framework, or number. Never blank an
> article, preposition, pronoun, auxiliary, or generic verb/adverb ("the", "a",
> "when", "buy", "deeply"). The auto-deriver (`scripts/derive-content.mjs`)
> enforces this — it only blanks a multi-word proper noun, a year, or a single
> word the pack explicitly *teaches* as a term — and the `scripts/cloze-quality.test.ts`
> audit fails the build if a derived blank is filler. When **hand-authoring** a
> cloze, follow the same rule: the one exception is a deliberate "pick the right
> value" drill where the answer is a common word but the distractors are the same
> category (e.g. the **two** natures of Christ with distractors `one/three/four`,
> or a Spanish reflexive **me** with `te/se/nos`).

---

## `comparison` — two images, pick the right one

Drives Right or Wrong. Side-by-side correct/incorrect with explanation.

```json
{
  "id": "cmp-3way-correct",
  "shape": "comparison",
  "prompt": "Which 3-way switch wiring will let either switch toggle the light?",
  "correct": {
    "caption": "Travelers between the two switches, commons to power and load",
    "imageSearchTerm": "3-way switch wiring diagram",
    "imagePrompt": "Clean schematic illustration of a correctly wired 3-way switch..."
  },
  "incorrect": {
    "caption": "Travelers wired into the wrong commons",
    "imageSearchTerm": "3-way switch wrong wiring",
    "imagePrompt": "Clean schematic illustration of an incorrectly wired 3-way switch..."
  },
  "explanation": "In a 3-way circuit, travelers carry signal between the two switches and commons attach to the power and the load.",
  "tags": ["electrical", "wiring"]
}
```

Each side has its own image. If `imageUrl` is missing on a side, the runtime shows the caption only.

---

## `trueFalse` — binary judgement with optional why-chain

Drives True or False? Bonus-point why-MCQ if `whyOptions` are provided.

```json
{
  "id": "tf-neutral-switch",
  "shape": "trueFalse",
  "statement": "On a single-pole light switch, the neutral wire passes through the switch alongside the hot wire.",
  "isTrue": false,
  "why": "Only the HOT wire is interrupted by the switch. Wiring a switch on the neutral side is a code violation.",
  "whyOptions": [
    "Only the hot wire is switched; neutrals pigtail straight through",
    "Both wires must pass through the switch by code",
    "It depends on whether the switch is upstream of the load"
  ],
  "whyCorrectIndex": 0,
  "tags": ["electrical", "wiring"]
}
```

`whyOptions` + `whyCorrectIndex` are optional. Without them, the game just shows the `why` text after the binary answer.

---

## `sentence` — tokens with canonical order

> **⚠ DROPPED (2026-07-08).** Removed from `schema.ts`; do not author. Retained
> here for historical reference only (no consuming game ever shipped).

For a future build-a-sentence game. `correctOrder` is a permutation of `[0..tokens.length-1]` giving the canonical order.

```json
{
  "id": "sent-quiero-cafe",
  "shape": "sentence",
  "tokens": ["Yo", "quiero", "un", "café"],
  "correctOrder": [0, 1, 2, 3],
  "translation": { "modality": "text", "value": "I want a coffee" },
  "tags": ["grammar", "food"]
}
```

No game consumes this shape yet — author it sparingly.

---

## `illustration` (optional, any item)

A supporting image attached to *any* item. The runtime shows it when present and falls back to text-only when absent.

```json
"illustration": {
  "kind": "photo",                                  // photo (default) | diagram | map | chart
  "url": "https://images.unsplash.com/photo-...",   // optional — `fetch-images` fills "photo" kinds
  "imagePrompt": "Wide-angle photograph of a busy modern airport terminal interior, floor-to-ceiling windows, warm afternoon sunlight, travelers walking with rolling luggage, photorealistic, shallow depth of field",
  "imageSearchTerm": "airport terminal interior",
  "alt": "Interior of a modern airport terminal with travelers and departure boards",
  "credit": "Unsplash · Jane Doe",                  // set by fetch-images for stock photos
  "creditUrl": "https://unsplash.com/photos/abc123" // link to the ORIGINAL photo page (not the raw CDN file)
}
```

- `kind`: optional. Controls how the fetcher treats this item.
  - `"photo"` (or unset) → script searches stock APIs (Unsplash → Pexels → Wikimedia Commons) and writes the first match to `url`.
  - `"diagram"` / `"map"` / `"chart"` → script *skips*; URL is expected to point at a curated SVG at `/packs/diagrams/<pack-id>/<item-id>.svg`. See `AUTHORING.md → Picking the right kind of visual` for the decision tree.
- `imagePrompt`: 30–60 words. Composition, style, lighting, mood, details (for photo); explicit element list, layout, palette (for diagrams).
- `imageSearchTerm`: 2–5 concise generic words. What you'd type into a search box.
- `alt`: short factual description for accessibility. **Required.**
- `url`: filled by `npm run fetch-images` for photo kinds; hand-set to the committed SVG path for other kinds.
- `credit` + `creditUrl`: image attribution. Set automatically for Unsplash by `fetch-images`; **keep the source link** (providers' terms require attribution that links back). Attribution lives here, on the image — never just at the pack level.

> **Pack-level fields** (alongside `items`/`lessons`): `packId`, `packName` (≤80),
> `packVersion` (`"N.N"` / `"N.N.N"`), `icon` (1–4 chars, emoji or initials),
> `shortName` (≤16, shown on fact-card eyebrows), `description` (≤400),
> `author`, `language`, `tagsVocabulary`. See [`KNOWLEDGE_PACKS.md`](KNOWLEDGE_PACKS.md) §3.

---

## Lesson / Part structure (optional but recommended)

After your `items` array, add `lessons`:

```json
{
  "items": [...],
  "lessons": [
    {
      "id": "l1-first-encounters",
      "title": "Lesson 1: First Words & Travel",
      "order": 0,
      "studyGuidePath": "/packs/guides/spanish-vocabulary/l1-foundations.md",
      "parts": [
        {
          "id": "l1p1-greetings",
          "title": "Part 1: Greetings & Courtesy",
          "order": 0,
          "blurb": "Hola, gracias, adiós — plus a couple of polite phrases.",
          "studyGuideAnchor": "greetings-and-courtesy",
          "itemIds": ["pair-hola", "pair-adios", "pair-gracias", "fact-greetings", "pair-cafe", "pair-agua"]
        }
      ]
    }
  ]
}
```

- **Part size: 6–10 items**. Smaller Parts lock out games that need ≥6 items.
- **Items can appear in multiple Parts** — use this for review parts that revisit earlier vocab.
- Without `lessons`, the runtime treats the whole pack as one synthetic Part (backward compat).

### Study guides

Every Lesson should ship with a **study guide** — a markdown article (~600–1,500 words) that teaches the lesson's content as prose, before the games quiz it. This is the *encoding* layer; the items are the *retrieval* layer.

Two fields wire it up:

- **`Lesson.studyGuidePath`** (string) — relative URL to the markdown file. Convention: `/packs/guides/<pack-id>/<lesson-id>.md`. The runtime fetches it on demand when the player opens the in-game Study button or the library syllabus.
- **`Part.studyGuideAnchor`** (string) — slug pointing at an `## h2` heading inside the guide. When set, the in-game Study button opens the guide scrolled to that section. Anchors are produced by [github-slugger](https://github.com/Flet/github-slugger) — lowercase the heading, strip punctuation, replace each whitespace char with a dash. `## A & B` → `a--b` (double-dash, because the `&` is stripped and the surrounding spaces both convert).

**Authoring rules:**

1. One `# h1` at the top with the lesson title.
2. One `## h2` per Part — the slugified id must match the Part's `studyGuideAnchor`.
3. Use `**bold**` for key terms — these are what the player will be tested on.
4. Talk to an adult. Same voice as items. Dry wit allowed, no cutesy.
5. Length: aim 600–1,500 words. Less than 600 isn't worth opening; more than 1,500 turns into a chore.

Reference implementations:
- `public/packs/guides/arizona-history/l1-prehistoric.md`
- `public/packs/guides/karpathy-zero-to-hero/l1-backprop.md`
- `public/packs/guides/san-diego-fishing/l1-landings.md`

Validation: **every Lesson must ship a `studyGuidePath`** — the Zod schema rejects packs that omit it. `Part.studyGuideAnchor` remains optional (a Part without one opens the guide at the top).

---

## When to use AI-generated diagrams

The `illustration.url` and `comparisonSide.imageUrl` fields accept **either** an external photo URL (Unsplash) **or** a relative path to a committed SVG diagram. Use diagrams when:

- The subject is abstract (process, schema, relationship, layout)
- You need controlled visual comparisons (correct vs. wrong, where the difference is precise)
- Photos can't reliably capture what's being taught (chain-rule cascade, attention pattern, knot tying)

The committed-SVG path convention is `/packs/diagrams/<pack-id>/<item-id>.svg`. See `AUTHORING.md → AI-generated diagrams` for the full workflow.

## Shape compatibility cheat sheet

Indicative, not exhaustive — the runtime matches games to shapes by their accept
list, and games come and go. Run `npm run audit:matrix` for the live grid.

| Shape | Games that consume it |
|---|---|
| `pair` | Quiz Cards, Lightning Round, Memory Flip, Word Hunter, Word Scramble, Word Search, Audio Catch, NPC Dialogue, Whack Word, Sort the Pile, Trivia Bet, Highway Hunt |
| `mcq` | Quiz Cards, Lightning Round, Trivia Bet, NPC Dialogue |
| `definition` | Term Drill, Word Hunter, Word Scramble, Sort the Pile, Whack Word, NPC Dialogue |
| `numeric` | Higher or Lower, The Estimator, Magnitude Stack |
| `fact` | feed cards (regular / hero / map) — no quiz game |
| `concept` | Who Is It? (person), Where Is It? (place), What Is It? (thing) |
| ~~`video`~~ | *dropped 2026-07-08* |
| `procedure` | Sequence It, Snake |
| `cloze` | Fill the Blank |
| `comparison` | Right or Wrong |
| `trueFalse` | True or False?, Right or Wrong |
| ~~`sentence`~~ | *dropped 2026-07-08* |
