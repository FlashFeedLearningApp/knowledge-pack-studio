# FlashFeed Knowledge-Pack Rework Plan

> **✅ COMPLETED 2026-07-09.** The two big asks are done: **image attribution** (all
> photos re-sourced stock-first, deduped, vision-QC'd, 0 uncredited — see
> [PROVENANCE.md](PROVENANCE.md)) and **shape balance + structure** (T/F retuned & capped,
> MCQ authored per section, synthetic banks dissolved, concepts + cloze enriched — corpus
> `noMcq`/`noQuiz`/`barren`/`thin` all 0). This file is now the historical record of that
> effort. The **durable standard** lives in [SHAPES.md](SHAPES.md) → *Shape
> Standard* and how to measure it in [AUDIT.md](AUDIT.md).

The laundry list of content + pipeline rework, from the 2026-07-08 review. Two asks dominate
(the "big ones"): **image attribution for every image** and **shape balance + structure
consistency across packs**. The shape POV + per-pack gap analysis below came out of a 25-agent
analysis (`pack-shape-pov` workflow) grounded in the dashboard's cross-pack data.

**Scope — the 20 GA packs only.** Deprecated packs are NOT reworked:
`4runner-3rd-gen`, `karpathy-zero-to-hero`, `san-diego-fishing`, `wildlife-recognition`
(plus the `az-history-candidate` draft). They stay served for existing installs but get no
further work.

---

## The three systemic problems (what the 20-pack analysis converged on)

1. **True/False inversion.** `trueFalse` is **34% of the whole corpus and the *plurality* shape in
   almost every pack** (40%+ in several) — over-derived (the deriver emits a T + F per seed) and the
   cheapest, lowest-difficulty 50/50 shape. It should be a *capped, harvested skin*, never grown.
2. **MCQ starvation.** `mcq` is **4.5% and absent from 54% of parts** — yet it's the default
   Lock-It-In game and the richest quiz material. The single biggest coverage gap to close.
3. **Broken cohesion.** Appendix/holding-pen **banks**, **orphan** items, **oversized parts**
   (up to 51 items), **missing `studyGuideAnchor`s**, and **thin/zero fact carousels** break the
   guide → carousel → Lock-It-In chain in most packs.

Plus the two cross-cutting items: **unattributed images** (Track A) and the **dead `video`/`sentence`
shapes** (dropped below).

---

## Track A — Image attribution & provenance  🔴 critical

**Why:** the provenance investigation (2026-07-08) found the ~706 "unattributed" cached photos have
**unrecoverable provenance** — a *mix* of Google Imagen 3.0 generations (the legacy `pack-generator`
web tool), Wikidata/Wikimedia (public-domain, attribution lost), Unsplash/Pexels (stock, attribution
lost), and possibly **arbitrary pasted URLs (copyright risk)**. Only ~13 are *confirmed* gpt-image-1
(`IMAGE-GEN-QUEUE.md`). The resize step stripped C2PA + EXIF, so per-file recovery is impossible.
**We can't treat the unattributed set as "ours."**

- **A1 — Eliminate every unattributed image.** Per image: **re-generate** via `gpt-image-1` (records
  provenance + embeds C2PA) → credit `AI-generated (gpt-image-1)`; or **re-fetch** through the current
  `fetch-images` pipeline (Unsplash / Pexels / Wikimedia / Openverse / LoC) which records a real
  credit; or **drop to text-only**. Prioritize by the dashboard's per-pack **Unattributed** count.
- **A2 — The pipeline records + applies attribution for ALL images, generated included** (so
  "unattributed" only ever means "not yet processed," never "shipped"); every `image-manifest.json`
  entry carries a non-null `credit`; the app **Sources screen** shows the credit for every image.
- **A3 — Gate it.** A validator check **fails a pack if any image lacks attribution** (the POV's own
  release gate: *"every image carries its own `credit` + `creditUrl`"*).

---

## Track B — Data-shape balance (the POV)  🟡

> **The FlashFeed pack standard is COVERAGE-FIRST, AUTHORED-SOURCE-DRIVEN, and PART-COHERENT. A "good" pack covers all 10 live game-shapes (everything but the dropped video + sentence), is anchored by an authored substrate (fact + pair + definition + numeric + concept + well-made mcq + procedure/comparison where the topic supports them), and treats trueFalse/cloze/derived-mcq as CAPPED, harvested retrieval skins — never hand-authored, never a pack's plurality. The corpus is currently inverted (trueFalse 34.2% is the single largest category while mcq sits at 4.5% and is absent from 54% of parts); the target rebalances authoring effort into generative + elaborative shapes and lifts mcq. Everything resolves through the PART: one study-guide h2 section = one part = its carousel facts = its co-located seed items = its re-homed derived quiz, so a Lock-It-In round quizzes ≥90% on what was just reviewed. Bands bend to topic; the cohesion chain and the trueFalse cap do not.**

### Target shape profile

| Shape | Priority | Target |
|---|---|---|
| `fact` | 🔴 core | 12–20% of items; ≥3 per part (carousels fall back to a standalone card below 3). Each fact traces to a bolded term/claim in that part's guide h2 — the encoding + dual-coding layer. Teaches but never tests, so every fact must chain to a same-part retrieval item. |
| `pair` | 🔴 core | 10–20% of items; ≥a few per part, cluster ≥6 in a part to unlock part-scoped matching. THE highest-leverage authored shape — drives the matching family + Thread-the-Web AND is the #1 derivation seed for T/F and cloze. |
| `trueFalse` | 🔴 core | CAP at ~one-third and never let it be a pack's plurality; corpus is 34.2% today (inverted). NEVER hand-author — ~90% derived from pair/definition/fact. Grow its sources, not it. Every derived T/F re-homes to its source part and ships a why/whyOptions chain (the elaboration is its only durable value). |
| `definition` | 🟠 strong | 5–12% of items; author wherever the topic has key terms (target most packs — 20/21 active already have it). Term→meaning recall backbone that maps 1:1 to bolded guide terms and derives cloze. Only pure-vocab packs legitimately skip it. |
| `numeric` | 🟠 strong | 5–12% (higher for quantitative packs); needs ≥6 comparable-UNIT items clustered in one part or the round-builders skip it. Force it wherever the topic has dates/sizes/counts. |
| `mcq` | 🟠 strong | LIFT to 3–8% (from 4.5% today); author ≥1 into EVERY part where feasible — the scarce, chain-critical shape missing in 54% of parts. Hand-author competitive distractors + an `explanation`; do NOT lean on derived mcq (its distractors teach little). The default Lock-It-In game. |
| `concept` | 🟠 strong | 4–8%; must group ≥6 of the SAME conceptKind (person/place/thing) in a part or the game won't schedule — author in confusable sets, never singletons; clues never name the answer; fact-check every clue via derive→judge. |
| `cloze` | 🟡 supporting | 3–8%, mostly DERIVED (~76%) — a CAPPED skin. Ensure teachable terms/proper-nouns/years exist so the deriver blanks a KEY concept, never an article or filler word; attach to the originating part. Hand-author only deliberate pick-the-right-value drills. |
| `procedure` | 🟡 supporting | 0–5% (up to ~15% for how-to packs); add 5–8 genuinely ordered steps wherever a real sequence exists, skip otherwise — never manufacture steps (yields nonsense). |
| `comparison` | 🟡 supporting | ≥3 items where a genuine correct-vs-wrong A/B contrast exists (clears the 8→9 coverage bar); image-dependent, so favor curated diagrams over scraped photos and don't force it (only 11/21 have any). |
| `video` | ⛔ drop | DROP — remove from schema/target profile and generator; fold any real value into a hero fact + an authored mcq. |
| `sentence` | ⛔ drop | DROP — remove entirely from schema/target profile and generator; never author. |

**Dropped shapes:**
- video — 3/25 packs, 5 items, one effectively-unused consuming game (Watch & Catch), no reliable implementation path, weak retrieval, and an external dependency that breaks offline caching + per-image attribution. Fold value into a hero fact + authored mcq.
- sentence — 0/25 packs and no game consumes it; dead shape. Remove from the schema, target profile, and generator entirely.

**Tolerances (topic-flex):** The shape MIX (which shapes are present) is held roughly consistent pack-to-pack so game diversity is even; the DISTRIBUTION (percentages) flexes to the topic. Bands are best-cohort defaults to bend around, NOT quotas that justify forcing nonsense items. Specifically: (1) numeric is optional/near-zero for non-quantitative topics and runs high (≥12%) for quantitative ones; (2) procedure is 0% for non-sequential topics and up to ~15% for how-to packs — never manufacture steps; (3) comparison is optional and added only where a precise, ideally visual A-vs-B distinction genuinely exists; (4) definition may be skipped only by pure-vocab packs; (5) concept requires ≥6 same-kind confusables to be worth authoring — skip rather than ship singletons. HARD, non-flexing constraints regardless of topic: the trueFalse cap (~one-third, never the plurality, never hand-authored); the full guide→carousel→Lock-It-In cohesion chain resolving through the part; ≥8 of 10 live shapes covered; zero barren parts; and image attribution. A pack that is ≥45% one shape (e.g. spanish-vocabulary 59% T/F, world-numbers 57% numeric) is flagged as a single-shape-dominance imbalance smell — the fix is MORE authored variety, not more of the dominant shape.

---

## Track C — Structure standard: study guide → fact carousel → Lock It In  🟡

**The distribution problem, now measured (dashboard "Study-guide / part coverage").** A pack can be
rich overall yet leave most guide sections thin — coverage must be counted *per section*, not per
pack. Across **787 sections**: **450 (57%) have no MCQ**, 260 (33%) no True/False, **145 (18%) have
no quiz at all**, 156 (20%) carry fewer than 2 game-shapes (national-parks has 32 MCQs but 51 of its
81 sections have none). This is the concrete target for the per-pack rework: lift each *section* to
≥1 mcq + a quiz shape, not just each pack.

**The structure model (the cohesion chain):**

THE PART IS THE UNIT OF COHESION — guide section, carousel, and quiz all resolve to one part's itemIds (guide h2 ↔ part is 1:1). Per LESSON: ship one studyGuidePath (Zod-required), a 600–1,500-word guide with one h1 (lesson title) and exactly one ## h2 per part, every testable term in **bold** (those bolded terms are exactly what the items test); ~2–4 parts per lesson. Per PART (target 6–10 items; never <3): (1) studyGuideAnchor = github-slugger slug of its h2, so section↔part is 1:1; (2) CAROUSEL — ≥3 authored `fact` items, each mapped to a bolded term/claim in that part's guide section (what you read = what you're quizzed on); (3) SEEDS — ≥3–5 game-shaped items authored INTO the part spanning ≥2–3 shapes (prefer pair/definition/numeric plus concept/mcq/procedure/comparison as the topic supports) — both direct game fuel and derivation source; (4) at least ONE generative-recall shape (pair/definition/numeric/cloze) AND at least one elaborative shape (mcq-with-explanation / concept / comparison / procedure / trueFalse-with-why), plus its facts — no "barren" part (facts but zero same-part game item); (5) aim ≥1 mcq per part (the default Lock-It-In game and the main gap); (6) DERIVED QUIZ — the pipeline generates trueFalse + cloze (+ derived mcq) and RE-HOMES each into the SAME part as its source (never a lesson-level bank), so a Lock-It-In round draws ≥90% in-scope via prefer-then-top-up. Per-part game unlocking: ≥6 same-conceptKind for concept, ≥6 comparable-unit for numeric, ≥6 for part-scoped matching. Per PACK: cover all 10 live shapes (≥8 minimum); fact + pair in essentially every part; definition/numeric/mcq/concept present across most parts; trueFalse/cloze arrive via derivation; procedure/comparison only where the subject genuinely supports them.

### Authoring checklist (the bar every reworked pack must clear)

- [ ] Covers ≥8 of the 10 live game-shapes (ideally all 10 except where topic genuinely excludes numeric/procedure/comparison); zero `video` and zero `sentence` items.
- [ ] trueFalse ≤ ~one-third of items and NOT the pack's plurality shape; no trueFalse was hand-authored (all derived from pair/definition/fact seeds).
- [ ] No single shape ≥45% of items (single-shape-dominance smell).
- [ ] Every lesson ships a studyGuidePath resolving to a 600–1,500-word guide: one h1, exactly one ## h2 per part, every testable term in **bold**.
- [ ] Every part's studyGuideAnchor slug matches its guide h2 (section↔part is 1:1); parts sized 6–10 items; zero parts <3 items.
- [ ] Every part has ≥3 `fact` items forming a carousel, each traceable to a bolded term/claim in that part's guide section.
- [ ] Every part has ≥3 authored game-shaped SEEDS spanning ≥2–3 shapes (prefer pair/definition/numeric), plus ≥1 generative-recall shape AND ≥1 elaborative shape; no barren part (facts but zero same-part game item).
- [ ] ≥1 authored `mcq` per part where feasible, each with competitive distractors and an `explanation` (this is the coverage gap — deliberately lift it).
- [ ] Every authored trueFalse-source and every derived trueFalse carries a why/whyOptions chain; every cloze blanks a key term / proper-noun / number (never filler).
- [ ] Derived trueFalse/cloze/mcq are re-homed to their originating part (not a lesson-level derived bank); a Lock-It-In round drawn part-first hits ≥90% in-scope.
- [ ] Group-game minimums met wherever those shapes are used: concept ≥6 same-conceptKind per part, numeric ≥6 comparable-unit per cluster, ≥6 pairs for part-scoped matching.
- [ ] Topic-flex sanity: numeric present iff the topic has real quantities, procedure present iff real sequences exist, comparison present iff a precise A/B contrast exists — no forced/nonsense items.
- [ ] Every image carries its own `credit` + `creditUrl` on the item (a hard release gate, tracked separately).

---

## Cross-cutting pipeline changes (do once, benefits every pack)

> **✅ DONE 2026-07-08** (monorepo `414b4a0`, open repo `8f46f04`): 1 T/F per seed + purge
> hand-authored T/F + per-part ≤⅓ cap; dropped `video` (5 items) + `sentence` from the schema.
> **Corpus T/F 34% → 17%; parts over ⅓: 83 → 0; −2,170 redundant T/F items** (substrate untouched).
> Full suite 192 + derived-tf-quality 51 green; served content redeployed; seed re-bundled.
> *Still to do here: the attribution gate (Track A3) + lifting mcq authoring in the generator.*

- **Deriver (`scripts/derive-content.mjs`):** emit **~1 T/F per seed, not two** (drop the tf-t + tf-f
  doubling); enforce a **per-part T/F cap (~one-third)**; keep re-homing derived items into their
  source part; require a why/whyOptions chain on every derived T/F.
- **Kill hand-authored `trueFalse`** — all T/F comes from derivation; delete existing hand-authored
  ones (seen in vw-gti 33, buddhism 25, spanish-vocabulary 22, christianity, …).
- **Drop `video` + `sentence`** from the schema, the target profile, and the generator; delete the
  handful of `video` items (christianity, vw-gti, …) and fold value into a hero fact + an authored mcq.
- **Attribution gate** in the validator (Track A3).
- **Lift `mcq` authoring** into the generator's per-part flow so new/ reworked packs get ≥1 authored
  mcq-with-explanation per part by default.

---

## Per-pack rework (ordered by effort, then name)

Grades: 🟢 strong · 🟡 moderate · 🟠 needs-work · 🔴 thin. Full task lists + shape gaps live in the
workflow output; the top tasks per pack:

| Pack | Grade | Effort | Top rework tasks |
|---|---|---|---|
| **arizona-history** | 🟡 moderate | heavy | • De-bank the variety (the structural fix): dissolve the appendix bank lessons (l10 numeric, l11 pair/definition, lc concept) and re-home each pair/definition/numeric/concept item into the topical narrative part it belongs to, so every part carries >=2-3 authored seed shapes and matching/numeric/concept/Lock-It-In games fire in-topic against guide-aligned carousel facts.<br>• Author pairs from 8 -> ~40-60 and seed 1-2 into every narrative part (the highest-leverage authored shape and primary T/F+cloze derivation source, currently near-absent).<br>• Cap cloze: cut derived cloze from 91 (24.5%) toward ~30-40 (<=8%), pruning filler/duplicate blanks and keeping only key-term/year/proper-noun blanks — the derived retrieval layer is cloze-inflated. |
| **azt-rincon-catalina** | 🟡 moderate | heavy | • Hand-author ≥1 real mcq (competitive distractors + explanation) into each of the ~19 mcq-less parts — the pack's 29 mcq are 100% derived (mcq-c-*), zero authored; mcq is the default Lock-It-In game and the biggest coverage gap.<br>• Attribute the 75 unattributed images (of 91) with per-item credit + creditUrl — hard release gate; only 16 currently credited (wikimedia).<br>• Author ≥3 comparison items (e.g., Rincon vs Catalina profile, correct-vs-wrong route/water decision) with attributed A/B visuals to add the missing SWING shape and lift coverage 8→9. |
| **best-life** | 🟡 moderate | heavy | • Fix the trueFalse inversion (hard-constraint violation): cap derived T/F to ≤~one-third overall and per-part so it is no longer the plurality (trim ~224→~180), which also shrinks the 34 oversized parts back toward 6–10 items — grow pair/definition/fact seeds instead of T/F.<br>• Restore the carousel chain: author ≥3 guide-anchored fact items into each of the 33 under-3-fact parts (~+90 facts), prioritizing the 0-fact parts (l10-p2-the-books, all l11 and l12 parts), each mapped to a bolded guide term.<br>• Lift mcq coverage: author ≥1 mcq with competitive distractors + explanation into each of the ~23 mcq-less parts (raise mcq ~4%→~8%) and add explanations to the 3 mcq missing them — this closes the single biggest game-fuel gap. |
| **critical-care-nursing** | 🟡 moderate | heavy | • Rebalance trueFalse (top hard-constraint fix): cap derived TF at <=one-third per part and grow the authored substrate so TF (343, 38.2%) falls under 33% and below pair (202) and is no longer the pack's plurality shape.<br>• Right-size the 44 oversized parts (10-51 items) into ~6-10-item parts with 1:1 guide sections; this simultaneously dissolves the 15 parts that are >=45% TF and caps per-part derivation.<br>• Add the missing comparison shape: author 6-8 A/B contrast items in shock types, DKA vs HHS, SIADH vs DI, and sodium disorders to reach 9/10 shapes covered and unlock Right-or-Wrong. |
| **diy-skills** | 🟠 needs-work | heavy | • Rebuild fact carousels pack-wide: author ~40 fact items so every part has >=3 facts, each tied to a bolded term in that part's guide h2 (restores the broken guide->carousel->quiz chain everywhere).<br>• Cap trueFalse: it is 82/204 (40.2%) and the plurality — trim over-derived low-value T/F and add authored variety so it drops below ~one-third and is no longer the dominant shape; grow its sources, not it.<br>• Author >=1 mcq per part (~16, currently 0 across all 16 parts) with competitive distractors + an explanation — the default Lock-It-In game and the largest coverage gap. |
| **investing-201** | 🟠 needs-work | heavy | • Cap and rebalance trueFalse from 198 (41.5%) to <=~one-third and no part >45%: prune the weakest ~50-70 derived T/F, stop deriving from every seed, and shift the retrieval load onto authored mcq + cloze. This is the hard-constraint fix and the highest priority.<br>• Lift mcq from 6 to ~1 per part: author ~22-28 hand-written mcq (competitive distractors + `explanation`) into the 32 parts that currently have none, restoring the default Lock-It-In game across the pack.<br>• Rebuild the carousel layer: author >=3 guide-anchored `fact` items into the ~27 fact-thin parts (9 of them have zero facts) so every studied guide section has a reviewable carousel that the co-located quiz then tests. |
| **last-economy** | 🟡 moderate | heavy | • Lift mcq from 4 to ~1 per content part (~15-24 items) with hand-authored competitive distractors + explanation - closes the single biggest shape gap and makes the default Lock-It-In game available part-scoped in the ~18 parts that lack it.<br>• Add >=3-6 authored comparison items on the book's natural A/B contrasts (Cathedral vs Bazaar, official vs human-reality dashboard, old vs new economy, Feudalism vs Symbiosis) with two attributed images each - lifts shape coverage 7 -> 8 and unlocks the comparison game family.<br>• Dissolve the orphan banks: re-home derived-cloze-orphan (2) and derived-mcq-orphan (2) into their source parts (kills both thin parts + the re-home violation), and give numerics-1/2 and cloze-1 a studyGuideAnchor + guide section (or fold them into content parts) so numeric/cloze join the cohesion chain. |
| **learning-theory** | 🟡 moderate | heavy | • Cap and prune trueFalse from 44.3% (216) down to <=one-third (~150), deleting ~70-120 derived T/F concentrated in the l10-vocabulary T/F dump (5 T/F-only parts) plus l7-p1 and l8-p2, and enforce a ~3-4 per-part T/F cap. Fixing the single-shape dominance is the headline task.<br>• Author fact carousels (>=3 facts per part, each traceable to a bolded guide term) into the ~28 carousel-less parts, prioritizing all 6 l10 parts and all 3 l9 parts (0 facts today). Restores the guide<->carousel<->quiz chain across the pack.<br>• Author >=1 hand-written mcq-with-explanation (competitive distractors) into each of the ~16 NO-MCQ parts, especially l10 and l9 — the default Lock-It-In game and the pack's part-level coverage gap. |
| **llm-101** | 🟡 moderate | heavy | • Author >=1 mcq per anchored part (~20-25 total, competitive distractors + `explanation`) - closes the pack's single biggest gap (0 -> ~7%), gives Lock-It-In its default game, and mechanically pushes trueFalse below the plurality line.<br>• Dissolve the 4 synthetic no-anchor holding-pen parts under Lesson 1 (numerics-1/2/3, procedures): re-home each numeric/procedure item into its topical anchored part (or L6's numeric parts), delete the 2-item thin numerics-3, and set anchors key-people/key-things on lc-people/lc-things to close their broken chain.<br>• Rebalance trueFalse below the cap and below pair: split/trim the 32-item l7 recall mega-part (redistribute its 12 pairs into topical parts), convert the 11 hand-authored TF to derived-or-reclassified, and add whyOptions to the elaboration chain. |
| **national-parks** | 🟡 moderate | heavy | • Break the trueFalse plurality by lifting mcq: author >=1 mcq (competitive distractors + explanation) into each of the ~50 parts missing one, raising mcq from 2.9% toward ~5% and pushing trueFalse below fact as the leading shape.<br>• Split the 60 oversized parts (median 13, max 33 items) into 6-10 item clusters, each aligned 1:1 with a single guide h2 section, so Lock-It-In rounds stay >=90% in-scope.<br>• Author definitions for bolded guide terms across the many parts lacking one (definition is only 1.7% / 6 of 79 parts) to reach the 5-12% band and seed additional derived cloze. |
| **spanish-vocabulary** | 🟠 needs-work | heavy | • Build the fact carousels: add ≥3 facts to every part (~100+ new facts), each traceable to a bolded term/claim in that part's guide h2 — currently 0/38 parts qualify, which is the single biggest cohesion break.<br>• Break the trueFalse inversion: retune scripts/derive-content.mjs to emit ~1 T/F per pair/definition/fact seed instead of 2, and cap derived trueFalse to ≤~one-third so it stops being the plurality (down from 445 / 59.4%).<br>• Delete the 22 hand-authored trueFalse items and regenerate T/F from seeds only (no hand-authored T/F). |
| **world-numbers** | 🟠 needs-work | heavy | • Break the numeric monoculture (98/171 = 57%, the explicitly-flagged dominance smell) by authoring the fact carousel every part is missing: add facts to reach >=3 per part (~40 new facts), prioritizing the 6 zero-fact parts (l2-p2-land, l3-p1-cities, l6-p2-symbols, l8-p1-superlatives, lc-places, lc-things). Each fact must trace to a bolded term/claim in that part's guide h2 -- this single move fixes BOTH the >45% dominance smell and the broken guide<->carousel chain. Do not add more numeric.<br>• Lift mcq to >=1 authored per part with competitive distractors + an explanation: 9 of 17 parts currently have zero mcq (l1-p2-monuments, l1-p3-mountains, l2-p2-land, l3-p2-nations, l4-p1-distances, l6-p2-symbols, l7-p1-records, l8-p1-superlatives, lc-places, lc-things), so Lock-It-In in those parts falls back to derived T/F only. mcq is the default Lock-It-In game and the corpus-wide coverage gap.<br>• Set studyGuideAnchor on the two Key Concepts parts -- lc-places -> 'key-places', lc-things -> 'key-things' -- both are currently null even though l-key-concepts.md already has matching '## Key Places' / '## Key Things' h2 sections. Without anchors these 12 concept items never resolve through the part, breaking the cohesion chain for the whole concept lesson. |
| **buddhism** | 🟡 moderate | medium | • Lift mcq from 15 to ~24: author one competitive-distractor mcq with an explanation into each of the ~9 substantive parts that have zero (l3p1, l3p2, l5p1, l6p1, l7p1, l9p1, l10p1, l11p2, l12p2) — closes the single biggest coverage gap and gives every content part a Lock-It-In default game.<br>• Break the trueFalse plurality: cap re-homed derived TF per part (~25-30%) so l2p2/l4p1/l4p2 stop being ~50% TF, and convert the 25 hand-authored TF into pair/definition/mcq seeds — target TF below fact (94) so it is no longer the pack's #1 shape.<br>• Fix l7p2-morals: add a 'The Morals' guide section with >=3 carousel facts so its anchor resolves and the part joins the guide->carousel->quiz chain (currently 0 facts, no guide, only pair/mcq/TF). |
| **christianity** | 🟡 moderate | medium | • Break the trueFalse plurality (HARD-constraint fix, highest impact): cap the deriver to 1 T/F per seed (drop the tf-t+tf-f doubling) with a per-part cap, and re-seed the 34 hand-authored trueFalse (l*-tf-*) as pair/definition/fact items so they derive instead — driving trueFalse from 212 (37.2%) to below fact (96) and under one-third, while preserving why/whyOptions chains.<br>• Lift mcq from 15 (2.6%) into the 3–8% band: hand-author ≥1 mcq with competitive distractors + an `explanation` into each of the ~17 core topical parts currently missing one; add explanations to (or drop) the 2 derived l14 diagram mcqs.<br>• Drop the video shape: delete the single video item and its l14p7-watch part — this also clears the pack's only thin part in one move; fold the content into a hero fact + an authored mcq. |
| **crochet** | 🟡 moderate | medium | • Break trueFalse's plurality: cap derived tf to ~3-4 per part (trim the worst offenders vocab-p2=15, mat-p1=12, vocab-p3=12, tech-p3/culture-p2/comm-p1=10) and lift authored pair/definition/mcq so pair becomes the top share and tf falls to ~one-quarter.<br>• Add >=3-6 comparison items (crochet-vs-knitting, US-vs-UK, wool-vs-acrylic, sc-vs-dc) with attributed diagrams to reach 10/10 live shapes.<br>• Lift mcq to >=1 per part: hand-author ~14 new mcq with competitive distractors + explanations into the mcq-less parts; add explanations to the 2 derived mcq that lack them. |
| **infinity-machine** | 🟡 moderate | medium | • Break the trueFalse plurality: it is 34.8% and the single largest shape (106 > fact 77), violating the hard cap. Trim ~30 derived T/F (keep only those with a solid why/whyOptions chain, re-homed to source parts) so T/F falls to <=~one-third and is no longer the pack's plurality.<br>• Lift mcq across parts: author >=1 mcq with competitive distractors + an explanation into each of the ~20 parts that currently lack one (mcq is in only 9/29 parts, 3.0%), making Lock-It-In's default game available part-wide and raising mcq toward 5-8%.<br>• Fix the orphan/derived-bank problem: attach the 2 orphan scrapbook items to their source parts, re-home their derived cloze+mcq into those same parts, and delete the lesson-level 'derived-cloze-orphan'/'derived-mcq-orphan' bins — this simultaneously clears the 2 orphan items and the 2 thin parts. |
| **philosophy** | 🟢 strong | medium | • Fill the fact carousels: 17 of 37 parts fall below the >=3-fact floor (all 6 concept-only l11 key-concept parts have 0 facts; ~9 doctrine parts have exactly 2), so half the pack has no real carousel. Author 1-2 fact cards per under-3 part, each traceable to a bolded term in that part's existing guide.<br>• Turn on / expand cloze derivation: only 1 cloze exists in 436 items (0.2% vs 3-8% target). Derive cloze from the 79 pair + 39 definition seeds, blanking key terms / proper-nouns / years, and re-home each to its source part (target ~15-30).<br>• Wire the cohesion chain: populate studyGuideAnchor on the 9 parts missing it (l1p2-distinctions + all 6 l11 parts, whose per-part guide files already exist) so guide<->part<->derived-quiz resolves everywhere, not just 28/37 parts. |
| **southern-az-gardening** | 🟡 moderate | medium | • Author mcq across the pack: lift from 1 (derived) to >=1 hand-authored mcq per topical part (~20-25 total), each with competitive distractors and an explanation and tied to that part's bolded guide terms — this closes the single biggest gap and fixes the default Lock-It-In game (30/31 parts currently have no mcq)<br>• Fix the 4 studyGuideAnchor slug mismatches (peppers-and-chiles->peppers-chiles, corn-beans-and-squash->corn-beans-squash, lettuce-and-spinach->lettuce-spinach, javelina-and-wildlife->javelina-wildlife) so the guide<->part<->carousel cohesion chain resolves via github-slugger<br>• Re-home the anchorless factless game-cluster parts: distribute the 14 'Numbers 1/2/3' numeric items into their topical guide-aligned parts (giving each an anchor + living beside its carousel facts), and either anchor or fold the glossary/right-or-wrong/key-things utility parts into guide sections; fix the thin numerics-3 (2 items) in the process |
| **sticky-apps** | 🟡 moderate | medium | • Break the trueFalse plurality/cap: prune ~50-65 derived TF (retain the best why-chained ones), weighting cuts to the 16 parts over 40% TF, until TF is below one-third and fact/pair are the top shapes again. This simultaneously shrinks oversized parts toward the 6-10 target.<br>• Lift mcq into the 17 mcq-less parts — author ≥1 competitive-distractor mcq with an explanation per part, prioritizing content parts (l3/l4/l5-net-p4/l6-viral-p2/l7-ret-p3/l8-dp-p2/l9-cases-p3); also add explanations to the 8 mcq that lack them.<br>• Close the guide/cohesion breaks: write guides/l7-ret-p3-investment-cohorts.md and set that part's studyGuidePath; wire the l10 concept parts to l10-concepts.md (populate studyGuidePath) and add the missing l10-p3-right-or-wrong anchor. |
| **vw-gti** | 🟢 strong | medium | • Rebalance trueFalse off the plurality: delete the 33 hand-authored trueFalse and tighten the per-part derived-TF cap so trueFalse falls below the fact count and under one-third, leaving it a derived-only skin — every survivor re-homed to its source part with a why/whyOptions chain.<br>• Lift mcq from 11 to ~36: hand-author >=1 mcq (competitive distractors + explanation) into each of the 26 mcq-less parts, making it the default Lock-It-In game everywhere and displacing trueFalse as the largest category.<br>• Drop the video shape: remove the single video item plus its 1-item l13p6-watch part, folding content into a hero fact + one authored mcq (also clears the pack's only thin-part gap). |

---

## Sequencing

1. **Agree the POV** (Track B/C above) — this is the authoring standard everything is reworked against.
2. **Cross-cutting pipeline changes** — the deriver T/F cap + drop video/sentence + attribution gate;
   these fix the #1 systemic problem (T/F inversion) across *all* packs in one pass.
3. **Re-attribution pass** (Track A) — the launch-blocking one; runs per-pack in parallel with the rest.
4. **Per-pack shape + structure rework** — regenerate/rebalance against the POV, worst-first per the
   table (needs-work/heavy packs: diy-skills, investing-201, spanish-vocabulary, world-numbers,
   learning-theory, national-parks).
5. **Fold the POV into `docs/KNOWLEDGE_PACKS.md`** so new packs are born compliant.
