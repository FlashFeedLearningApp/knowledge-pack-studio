# Auditing & Evaluating Packs

How to measure the health of the knowledge packs — what shapes they carry, how
well each study-guide section is covered, and where the gaps are. This is the
companion to **[SHAPES.md](SHAPES.md)** (what each shape is) and
**[KNOWLEDGE_PACKS.md](KNOWLEDGE_PACKS.md)** (the canonical authoring spec).

The audit answers three questions:

1. **What's in each pack?** — the shape mix (facts, pairs, definitions, mcq,
   concept, cloze, trueFalse, numeric, comparison, procedure).
2. **Is every section playable and quiz-able?** — per-**part** coverage (a part =
   one study-guide `<h2>` section = the unit of cohesion).
3. **Are the images real and attributed?** — provenance per pack.

---

## Running it

```bash
npm run validate          # schema + attribution gate (CI gate; exits non-zero on failure)
npm run build-dashboard   # tools/build-dashboard.ts → dashboard/analysis.json (+ console summary)
npm run dashboard         # build-dashboard + serve the visual dashboard at localhost
```

- **`validate`** is the hard gate: every pack must pass the schema *and* the
  attribution rule (any image under `generated/` must carry a `credit`). Run it
  after any content change and in CI.
- **`build-dashboard`** computes every metric below into `dashboard/analysis.json`
  and prints a per-pack table. Nothing is computed in the browser — the static
  dashboard just renders the JSON.
- All corpus rollups count **active packs only** (`status` `ga` or `preview` in
  `catalog.config.json`); deprecated/draft packs are excluded so we don't chase
  metrics on content we're not shipping.

---

## The metrics

### Shape totals & coverage
- **`shapeTotals`** — count of each shape across active packs.
- **`shapeCoverage`** — how many packs contain at least one of each shape. A shape
  absent from most packs is a systemic gap (e.g. `concept` was in <15% of lessons
  before the enrichment pass).

### Part coverage (the core health metric)
Computed per **real part** (synthetic `::` banks are excluded — they were never
study-guide sections). Each is a count of parts that FAIL the bar:

| Metric | A part is counted when… | Why it matters |
|---|---|---|
| `thin` | it has **< 3 items** | too little to build a carousel or round from |
| `noMcq` | it has **no `mcq`** | no authored multiple-choice for that section |
| `noTrueFalse` | it has **no `trueFalse`** | (soft — T/F is derived-only & capped, so some parts legitimately have none) |
| `noQuiz` | it has **no `mcq`, `trueFalse`, or `cloze`** | the section can't be quizzed *at all* — the worst signal |
| `barren` | it has facts but **0 game-shapes** | there's content to read but nothing to play |
| `underShaped` | it has **< 2 game-shapes** | only one way to play the section; monotonous |
| `partsNoAnchor` | the part has **no `studyGuideAnchor`** | breaks the guide→carousel→quiz cohesion chain |
| `lessonsNoGuide` | the lesson has **no `studyGuidePath`** | no study guide backing the lesson |
| `avgShapes` | (not a failure) average distinct shapes/part | overall richness dial |

**Target: every real part scores 0 on `noQuiz`, `barren`, and `thin`.** As of the
2026-07 rework, active packs sit at `noMcq`/`noQuiz`/`barren`/`thin`/`underShaped`
= **0**; `noTrueFalse` is the only nonzero one and that's expected (T/F is a capped
derived skin, not required per part).

### Image provenance (`imageSources`)
Per pack, classified from each `illustration.credit`:
- **Pexels / Unsplash** — commercial stock, attributed.
- **Wikimedia / Openverse** — openly-licensed (PD/CC), attributed.
- **AI-generated (gpt-image-1)** — our own pipeline; we own it.
- **unattributed** — an image with a URL but **no credit**. This should be **0**.
  The 2026-07 re-source pass drove it to zero; `validate` keeps generated images
  from regressing, and a served-content audit should show 0 uncredited remote
  images.

### Comprehensiveness & gaps
- **`comprehensiveness`** — a rough 0–100 per-pack roll-up of shape breadth + part
  coverage, for ranking which packs need work.
- **`gaps`** — human-readable flags per pack (e.g. "12 thin parts (<3 items)",
  "3 lessons with no study guide").

---

## How to read a result

1. **Sort by `noQuiz` / `barren`** — those are the packs with unplayable sections.
   Fix by authoring an `mcq` (or ensuring the part has a definition/pair/fact that
   derives a cloze) for each flagged part.
2. **Scan `imageSources` for `unattributed > 0`** — a licensing risk. Re-source
   (stock-first) or attribute.
3. **Check `partsNoAnchor` / `lessonsNoGuide`** — structural breaks in the
   guide→carousel→Lock-It-In chain; fix the anchors/guide paths.
4. **Use `avgShapes` + `shapeCoverage` as richness dials** — low `concept`/`cloze`
   coverage means a shape-enrichment pass is due (see SHAPES.md → *Shape Standard*).

The visual dashboard (`npm run dashboard`) renders all of this as a heatmap so the
worst cells jump out; the console table from `build-dashboard` is the same data
for quick diffs.

---

## Content quality

Coverage (above) asks *"is there something to play here?"*. Content quality asks
*"is what's here any good?"* — measured in two tiers by how reliably each signal
can be judged. Everything surfaces in the dashboard's **Content Quality** section
(per-pack heatmap; click a pack for the flagged items).

### Tier 1 — deterministic (free every build, CI-gated)

Computed by `build-dashboard.ts`; the hard ones also gate `npm run validate`:

- **Answer-in-clue leaks** — a game must never show a clue/prompt that spells its
  own answer (the "…or GDP" bug: a Knowledge Wheel clue built from a definition
  read "we started with gross domestic product or GDP"). The rule: **for `mcq`,
  `concept`, `cloze`, and `pair`, the visible text must not contain the answer
  verbatim** (word-boundary, case/accent-insensitive — mirrors the mobile runtime
  `clueLeaksAnswer` guard). **Hard gate.** Corpus is at **0**.
- **MCQ integrity** — every option must be distinct (a duplicate makes the
  question unanswerable). **Hard gate.** Too-few options (<4) is a softer signal,
  surfaced but not gated.
- **Attribution** — measured on **stock** images only (the licensing-critical
  set). Our own `generated` assets carry no third-party credit by design and are
  tracked separately, not penalised. Corpus stock-attribution is **100%**.

**Not a leak:** a `definition` whose text names its term ("Elevation is the height
…") is correct for a study card and is de-leaked at the game layer — don't rewrite
definitions to hide their term.

### Tier 2 — LLM semantic judge (`tools/judge-content.wf.js`)

Some quality can't be judged by string rules. The clearest case is **MCQ category
coherence** — *"Which U.S. president signed the treaty?"* with options
[Washington, democracy, the economy, a tax bill] needs no knowledge because only
one option is a person. A surface heuristic (capitalisation, length) is ~all
false positives ("Mexican spotted owl" vs "Elf owl" look different but are both
owls), so this is judged by an LLM. The judge scores every MCQ on category
coherence, answer correctness, and distractor plausibility; **each flag is then
re-checked by an independent skeptic** to kill false positives. Run it as a Claude
admin Workflow (see the file header); it writes `dashboard/content-quality.json`
(merged into the dashboard) + `qa-reports/content-quality-<date>.md`.

First full pass (2026-07-10): **760 MCQs → 7 broken + 46 weak** (skeptic-confirmed,
7% of MCQs). **46 of the 53 were derived `mcq-c-*` MCQs** — the deriver's cloze→MCQ
path picked distractors from a pool that wasn't constrained to the blanked answer's
category, so the answer was identifiable by category alone. **Fixed** by a
skeptic-verified regeneration pass: the 46 cloze-derived fixes are pinned as
`curatedDistractors` on their source facts (the deriver's cloze→MCQ path prefers
them, so a re-derive reproduces the fix); the deriver also gained a `nearDupe`
filter for the near-duplicate / fragment class; the 7 authored MCQs were baked
directly. A verification re-judge on the 14 changed packs returned **0 broken**
(the 3 residual `weak` were different items the first pass missed, also fixed).
**Corpus is now 0 broken + 0 weak.** (qa-reports/content-quality-2026-07-10.md)

Re-run the leak scan and the judge after any content change; deterministic leaks /
dup-options should stay at **0**.
