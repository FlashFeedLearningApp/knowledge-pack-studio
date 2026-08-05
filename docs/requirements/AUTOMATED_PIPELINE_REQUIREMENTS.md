# Automated Knowledge-Pack Pipeline — Product and Engineering Requirements

**Status:** Draft for implementation planning  
**Audience:** Product, content, curriculum, AI/LLM, data, platform, and QA engineers  
**Normative language:** **SHALL** and **MUST** are release requirements; **SHOULD** is a default that may be overridden with a recorded reason; **MAY** is optional.  
**Primary output:** A self-contained FlashFeed knowledge-pack folder containing a schema-valid `pack.json`, study guides, licensed or first-party visual assets, provenance, and machine-readable QA evidence.

---

## 1. Purpose

This document specifies an automated, LLM-assisted pipeline that turns a requester's idea into a publishable learning knowledge pack.

The pipeline must do more than generate JSON. It must:

1. turn an underspecified idea into an approved learning brief;
2. research the topic and preserve claim-level evidence;
3. write a study-guide-style teaching substrate;
4. create a coherent lesson and part structure;
5. produce content in the shapes supported by the consuming application;
6. source or create lawful, relevant, accessible images;
7. derive selected retrieval items deterministically;
8. validate structure, facts, pedagogy, ratios, assets, and runtime playability;
9. expose uncertainty and exceptions for human review; and
10. emit reproducible artifacts and an auditable release decision.

The core quality model is:

> **One part = one study-guide section = one fact carousel = one local retrieval pool.**

The pipeline is successful only when what the learner reads, sees, and is tested on remains aligned at the part level.

---

## 2. Goals and non-goals

### 2.1 Goals

The system SHALL:

- accept anything from a one-sentence idea to a detailed content brief;
- decide whether clarification is necessary and conduct a bounded requester interview when it is;
- produce adult-readable study guides supported by authoritative sources;
- use a pinned consumer schema rather than an LLM-invented schema;
- produce accurate, varied, playable items with strong distractors and explanations;
- enforce hard release gates and report softer target-band exceptions separately;
- prefer deterministic transformations and checks where possible;
- use independent semantic review for judgments that cannot be made reliably with string rules;
- be resumable, idempotent, observable, and cost-aware;
- preserve the evidence necessary to explain why every material claim, image, and release decision was accepted.

### 2.2 Non-goals

The first version SHALL NOT:

- redesign the FlashFeed runtime or add a content shape without a separately approved schema change;
- publish copyrighted prose, scraped press photography, or assets with unknown rights;
- treat passing JSON-schema validation as proof of factual or instructional quality;
- optimize for maximum item count;
- fabricate numeric values, quotations, citations, credentials, image credits, or source URLs;
- make high-stakes medical, legal, financial, or safety content fully autonomous;
- publish automatically when a mandatory human approval is outstanding.

---

## 3. Design principles

### 3.1 Evidence before content

Research and evidence capture SHALL precede guide and item generation. The LLM may propose a curriculum outline before research, but it MUST NOT finalize factual prose or answer keys until evidence has been gathered.

### 3.2 The guide is the teaching source of truth

The approved study guide is the encoding layer. Pack items are the retrieval and practice layer. Every testable item SHALL trace to a guide claim or a recorded supplemental source.

### 3.3 The part is the unit of cohesion

All authored items and their derived children SHALL remain assigned to the originating part. The pipeline SHALL NOT create pack-wide shape banks or lesson-level “miscellaneous quiz” pools.

### 3.4 Author rich seeds; derive cheap skins

Facts, pairs, definitions, numeric items, concepts, MCQs, procedures, and comparisons are authored substrate. `trueFalse` and `cloze` are derived retrieval skins and SHALL normally be machine-generated from approved seeds.

### 3.5 Coverage targets are not excuses for nonsense

Topic-dependent shapes SHALL be generated only when the subject supports them. The system MUST record why `numeric`, `procedure`, `comparison`, or `concept` was omitted rather than manufacturing weak content to hit a quota.

### 3.6 Deterministic checks first, semantic judges second

Syntax, references, counts, slugs, duplicates, attribution, and answer leaks SHALL be checked deterministically. Factual correctness, distractor plausibility, category coherence, pedagogical value, and image relevance require semantic review.

### 3.7 Generation and judgment are separate roles

The same LLM response SHALL NOT both create and finally approve an artifact. A separate judge pass, with a different prompt and no access to the author's hidden reasoning, SHALL assess semantic quality. Critical flags SHOULD receive an additional skeptic pass.

### 3.8 No silent repair

Every automatic change after initial generation SHALL be captured as a patch with a reason, originating validator or judge, before/after hash, and affected artifact IDs.

---

## 4. Key definitions

| Term | Meaning |
|---|---|
| Idea | The requester's initial statement of the topic or desired learning outcome. |
| Brief | The clarified, approved specification of audience, scope, outcomes, constraints, tone, and risk. |
| Claim | A discrete factual assertion that can be supported, contradicted, or marked uncertain. |
| Evidence ledger | Machine-readable mapping of claims to sources, excerpts or summaries, dates, and confidence. |
| Lesson | A curriculum unit with a study guide and approximately 2–4 coherent parts by default. |
| Part | The runtime scheduling and instructional-cohesion unit; corresponds to one guide `##` section. |
| Shape | The consumer-defined JSON form of a content item, such as `fact`, `pair`, or `mcq`. |
| Authored seed | A high-value item created from approved evidence and guide content. |
| Derived item | A deterministic or constrained transformation of an authored seed, such as `cloze` or `trueFalse`. |
| Hard gate | A condition that blocks release. |
| Quality target | A desired band that produces a warning or review request when missed, but may be waived. |
| Waiver | A recorded, approved exception containing scope, reason, risk, approver, and expiration or version. |

---

## 5. Actors and responsibilities

### 5.1 Requester

Provides the idea, answers material clarification questions, and approves the brief when required.

### 5.2 Pipeline orchestrator

Owns state transitions, artifact versioning, retries, caching, budgets, approvals, and final release status. The orchestrator SHALL be deterministic code, not an unconstrained LLM agent.

### 5.3 LLM roles

The implementation MAY use one model with isolated prompts or multiple models. Logical roles SHALL remain distinct:

- **Interviewer:** identifies ambiguity and asks the minimum useful questions.
- **Research planner:** creates queries and a source strategy.
- **Research synthesizer:** builds the evidence ledger without writing final pack content.
- **Curriculum architect:** creates lessons, parts, objectives, and a shape plan.
- **Guide author:** writes cited study-guide prose from approved evidence.
- **Item author:** produces authored seeds from guide sections.
- **Visual planner:** identifies where images add instructional value and specifies visual intent.
- **Semantic judge:** checks facts, alignment, pedagogy, and distractors.
- **Skeptic:** rechecks proposed failures and high-risk claims to reduce false positives.
- **Repairer:** patches only explicitly identified defects.

### 5.4 Human reviewer

Approves the brief, evaluates flagged claims and visual assets, grants waivers, and authorizes publication where policy requires it.

---

## 6. End-to-end state machine

The orchestrator SHALL implement the following resumable states:

```text
IDEA_RECEIVED
  -> TRIAGED
  -> [CLARIFICATION_REQUIRED -> WAITING_FOR_REQUESTER -> BRIEF_APPROVED]
     or [BRIEF_AUTO_ACCEPTED]
  -> RESEARCH_PLANNED
  -> EVIDENCE_READY
  -> CURRICULUM_PLANNED
  -> GUIDE_DRAFTED
  -> GUIDE_APPROVED
  -> ITEMS_AUTHORED
  -> IMAGES_PLANNED
  -> IMAGES_RESOLVED
  -> DERIVED_ITEMS_BUILT
  -> VALIDATED
  -> SEMANTICALLY_JUDGED
  -> REVIEW_READY
  -> APPROVED
  -> PACKAGED
  -> PUBLISHED
```

Any state MAY transition to `NEEDS_REPAIR`, `WAITING_FOR_APPROVAL`, `BLOCKED`, or `CANCELLED`. `NEEDS_REPAIR` SHALL identify the failing gate and return to the earliest state whose artifact must change. A downstream artifact invalidated by an upstream change SHALL be marked stale by dependency hash.

The pipeline SHALL NOT use a single opaque “generate pack” request because it prevents reliable resumption, targeted repair, and auditability.

---

## 7. Canonical artifacts and schemas

### 7.1 Schema policy

The system SHALL maintain two separate schema families:

1. **Consumer schema:** the pinned version of `@flashfeed/pack-schema`, used for the final `pack.json`.
2. **Pipeline schemas:** versioned JSON Schemas for briefs, evidence, curriculum plans, visual plans, validation reports, and run manifests.

The LLM SHALL NOT infer or rewrite the consumer schema from examples. The orchestrator SHALL load the installed schema version, record it in the run manifest, and reject output containing unsupported shapes or fields.

If a requested experience requires a new shape, the pipeline SHALL emit `SCHEMA_CAPABILITY_GAP` and a separate schema-change proposal. It SHALL NOT mutate the pack contract inside a content-generation run.

### 7.2 Required run artifacts

Each run SHALL preserve:

```text
runs/<run-id>/
  run-manifest.json
  idea.json
  interview.json
  brief.json
  research-plan.json
  evidence-ledger.json
  curriculum-plan.json
  guide-outline.json
  guide-drafts/
  item-plan.json
  item-drafts.ndjson
  visual-plan.json
  image-ledger.json
  derivation-ledger.json
  validation-report.json
  semantic-review.json
  waivers.json
  patches.ndjson
  release-report.json
```

The publishable folder SHALL remain clean and consumer-facing:

```text
packs/<pack-id>/
  pack.json
  guides/
  diagrams/
  images/
  generated/
```

### 7.3 Run manifest minimum fields

`run-manifest.json` SHALL include:

- `runId`, `createdAt`, `updatedAt`, `status`;
- requester and project identifiers, subject to privacy policy;
- pipeline version and source revision;
- consumer schema package name and exact resolved version;
- model provider, model identifier, prompt-template version, and generation parameters for each LLM call;
- input and output hashes for every stage;
- source-retrieval timestamps;
- token, latency, tool-call, and monetary-cost totals by stage;
- approval and waiver references;
- final pack version and artifact checksums.

### 7.4 Brief schema requirements

The approved `brief.json` SHALL contain at least:

- working title and stable `packId` candidate;
- idea summary in the requester's language;
- target audience, assumed prior knowledge, language, locale, and reading level;
- desired learner outcomes expressed with observable verbs;
- included topics, excluded topics, and boundary cases;
- intended breadth and depth;
- preferred tone and prohibited framing;
- time-sensitivity and “as of” date;
- risk classification;
- source constraints or requester-provided materials;
- image preferences, likeness restrictions, and brand constraints;
- desired size or learning-time budget, if supplied;
- acceptance criteria;
- unresolved assumptions;
- requester approval status and timestamp.

### 7.5 Evidence-ledger schema requirements

Each evidence record SHALL contain:

- stable `claimId`;
- normalized claim text;
- topic, proposed lesson, and proposed part;
- claim type: fact, definition, quantity, chronology, causation, procedure, opinion, controversy, or safety warning;
- one or more `sourceId` references;
- source-specific support summary and location within the source when available;
- publication date, retrieval date, author or institution, and canonical URL;
- primary/secondary/tertiary classification;
- authority score, recency score, independence group, and relevance score;
- agreement status across sources;
- confidence: high, medium, low, or disputed;
- time sensitivity and next review date;
- allowed uses: guide, answer key, numeric item, image caption, or background only;
- human-review requirement and reviewer disposition.

The ledger SHALL store short excerpts only when license and policy allow it. Final prose SHALL be original or properly licensed, not assembled by copying source passages.

### 7.6 Curriculum-plan schema requirements

The plan SHALL represent:

- ordered lessons and parts;
- one-sentence rationale and learning objective for each part;
- guide heading and deterministic slug for each part;
- claim IDs assigned to each part;
- planned authored items by shape and source claim;
- planned derived items and their seed IDs;
- planned visual opportunities and visual type;
- group-game cluster information for `concept` and `numeric`;
- estimated item totals and shape ratios;
- explicit topic-flex exclusions with reasons;
- coverage gaps and proposed repairs.

### 7.7 Image-ledger schema requirements

Each image candidate or generated asset SHALL include:

- `assetId`, target item IDs, and intended teaching purpose;
- kind: photo, diagram, map, chart, or scrapbook;
- search term or generation prompt;
- provider and exact source page;
- creator, license, license URL, and required attribution text;
- original URL, cached URL or relative asset path, MIME type, dimensions, byte size, and checksum;
- retrieval or generation timestamp;
- duplicate/perceptual-hash result;
- relevance, correctness, safety, quality, and accessibility review results;
- final alt text and caption;
- acceptance status and rejection reason.

---

## 8. Functional requirements by phase

## 8.1 Phase A — Intake and idea triage

### FR-A01: Preserve the original request

The pipeline SHALL store the request verbatim, a normalized summary, attachments, and known project context. Normalization SHALL NOT replace the original.

### FR-A02: Classify the request

The pipeline SHALL classify:

- topic domain;
- expected audience;
- desired outcome: awareness, recall, application, procedure, comparison, or mastery;
- breadth and likely pack size;
- time sensitivity;
- safety and policy risk;
- dependence on requester-specific knowledge;
- availability of authoritative sources;
- visual dependence;
- schema fit.

### FR-A03: Determine clarification need

Clarification SHALL be required if any material field below is unknown and cannot be safely defaulted:

- who will learn this;
- what learners should be able to do;
- what is in or out of scope;
- whether the content is descriptive or prescriptive;
- jurisdiction, locale, product version, or time period when relevant;
- required source set or private materials;
- high-stakes risk tolerance;
- size, deadline, or publication constraint that changes the design.

The pipeline MAY auto-accept a brief when ambiguity is low and all defaults are explicitly recorded.

### FR-A04: Detect unsuitable or infeasible ideas

The pipeline SHALL stop before research when the request is prohibited, irreducibly dependent on inaccessible private information, impossible within the consumer schema, or requires rights the requester has not supplied.

## 8.2 Phase B — Requester interview

### FR-B01: Ask high-information questions

Each interview turn SHALL ask no more than three concise questions. Questions SHALL be prioritized by their expected effect on curriculum, factual interpretation, risk, or acceptance.

### FR-B02: Avoid unnecessary interviewing

The interviewer SHALL NOT ask the requester to decide implementation details that can be derived from the repository's canonical standard, such as exact JSON field names or default shape ratios.

### FR-B03: Bound the interview

The default interview SHALL be one to three turns. After the third turn, the pipeline SHALL either:

- present a brief for approval with explicit assumptions;
- identify a material blocker; or
- request an approved exception for continued discovery.

### FR-B04: Resolve contradictions

If requester answers conflict, the system SHALL quote or reference the conflicting answers, explain their effect, and ask one resolution question. It SHALL NOT silently choose.

### FR-B05: Produce an approval-ready brief

The interview ends with a compact human-readable brief plus the machine-readable `brief.json`. High-risk, branded, or materially ambiguous work SHALL require explicit approval before research proceeds.

## 8.3 Phase C — Research and source acquisition

### FR-C01: Create a source strategy

Before searching, the research planner SHALL identify:

- claim categories that require sources;
- preferred primary authorities;
- likely contested or time-sensitive claims;
- geographic, cultural, and temporal coverage needs;
- minimum source diversity;
- sources to avoid;
- stopping criteria.

### FR-C02: Use a source hierarchy

The default order SHALL be:

1. primary sources, standards, official documentation, government data, or original research;
2. peer-reviewed synthesis or authoritative institutional references;
3. reputable specialist secondary sources;
4. general reference sources for orientation only.

User-generated or marketing material MAY establish a party's own claim but SHALL NOT independently validate that claim.

### FR-C03: Meet evidence minimums

- Every material guide claim SHALL map to at least one credible source.
- High-impact, contested, causal, safety-related, or rapidly changing claims SHALL have two independent credible sources unless a single canonical primary authority controls the fact.
- Numeric claims SHALL include unit, geography or population, time period, definition, and source date.
- Quotations SHALL be verified against a primary or authoritative transcript and remain within applicable quotation limits.
- “Current,” “latest,” or version-dependent claims SHALL record an as-of date and freshness policy.

### FR-C04: Track contradictions and uncertainty

The synthesizer SHALL preserve disagreements rather than averaging them away. Disputed claims SHALL be excluded, qualified in the guide, or escalated for review.

### FR-C05: Detect source circularity

Multiple pages repeating the same upstream claim SHALL count as one independence group. The system SHOULD identify citations that all trace to the same press release, dataset, or article.

### FR-C06: Resist prompt injection and untrusted instructions

Retrieved pages are evidence, not instructions. The research layer SHALL strip or quarantine page text that attempts to control the model, request secrets, modify policy, or redirect pipeline behavior.

### FR-C07: Apply research stopping criteria

Research may stop when:

- every planned material claim has adequate support;
- high-risk claims meet the stronger evidence rule;
- no unresolved contradiction blocks teaching;
- the curriculum can meet the approved outcomes; and
- additional searching produces diminishing new coverage.

## 8.4 Phase D — Curriculum and study-guide planning

### FR-D01: Design backward from outcomes

The curriculum architect SHALL map each learner outcome to one or more lessons, guide claims, authored items, and demonstrations or objective tests when those are in scope.

### FR-D02: Create coherent lessons and parts

- A lesson SHOULD contain approximately 2–4 parts.
- Each part SHALL cover one coherent subtopic or discrimination set.
- Each part SHALL map to exactly one `##` guide heading.
- Part ordering SHOULD move from prerequisites to application, comparison, or synthesis.
- The plan SHALL avoid catch-all, glossary-only, or shape-specific banks unless a glossary is itself an approved learning objective.

### FR-D03: Plan before prose

The curriculum plan SHALL be validated for outcome coverage, source coverage, part coherence, and projected shape viability before guide prose is generated.

## 8.5 Phase E — Study-guide generation

### FR-E01: Generate guide structure

Each lesson guide SHALL contain:

- one `#` heading matching the lesson title;
- exactly one `##` heading per part, in the same order;
- deterministic heading slugs matching `Part.studyGuideAnchor`;
- bold formatting for key terms and testable claims;
- source references sufficient to trace material claims;
- original prose appropriate to the brief's audience and tone.

### FR-E02: Meet guide length and usability targets

A lesson guide SHOULD be approximately 600–1,500 words. A shorter guide requires a recorded reason; a longer guide SHOULD be split unless cohesion would suffer.

Each section SHOULD:

- establish why the topic matters;
- explain key terms before using them heavily;
- connect new ideas to prior sections;
- distinguish commonly confused concepts;
- qualify uncertainty;
- include units, dates, and scope for quantities;
- avoid unsupported superlatives and causal claims.

### FR-E03: Run claim coverage

Every sentence containing a material factual assertion SHALL be matched to an approved claim or flagged for evidence review. The system SHOULD compute:

`guide_claim_coverage = supported_material_claims / material_claims`

Release target: `1.00`. Unsupported material claims are a hard failure.

### FR-E04: Approve guides before item generation

Items SHALL be generated from an evidence-checked guide version. A material guide change SHALL invalidate downstream items whose claim or section hashes changed.

## 8.6 Phase F — Consumer JSON construction and authored items

### FR-F01: Pin the consumer schema

The builder SHALL use the exact installed version of `@flashfeed/pack-schema` and record it in the run manifest. The final `pack.json` SHALL validate through `validatePack()` and repository-specific gates.

### FR-F02: Build metadata and hierarchy deterministically

The pipeline SHALL create stable kebab-case IDs, deterministic ordering, guide paths, and item references. IDs SHALL remain stable across reruns when the underlying semantic item is unchanged.

### FR-F03: Generate authored seeds part by part

For each part, the item author SHALL receive only:

- the approved brief;
- the relevant guide section;
- approved claims and source metadata;
- the part's shape plan;
- consumer field constraints;
- sibling items needed to avoid duplication.

It SHALL NOT receive unrelated raw web pages or permission to introduce new facts.

### FR-F04: Apply shape-specific requirements

#### `fact`

- Teaches rather than tests.
- Title and body SHALL comply with schema limits.
- Each fact SHALL map to a bolded guide term or claim.
- Each fact SHOULD link to or share a part with a retrieval item.

#### `pair`

- Sides SHALL express a meaningful teachable association.
- The answer side SHOULD be concise enough for games; use `short` when necessary.
- Pair text SHALL not leak one side verbatim into the other where the runtime treats it as a question.

#### `definition`

- Term and definition SHALL be precise at the audience's level.
- Definitions SHALL distinguish the term from nearby concepts, not merely restate its name.

#### `numeric`

- Value, unit, context, reference period, and evidence SHALL agree.
- Items grouped for play SHALL have comparable dimensions and sensible magnitude ranges.
- The pipeline SHALL NOT mix dates, lengths, populations, or currencies in one comparison cluster.

#### `mcq`

- Exactly four options SHOULD be authored even if the schema permits two to four.
- Exactly one option SHALL be unambiguously correct.
- Distractors SHALL be plausible, factually coherent, mutually distinct, and from the same answer category.
- The prompt SHALL not leak the answer.
- An explanation SHOULD state why the keyed answer is correct and, where useful, address the tempting misconception.
- Options SHALL survive the runtime's normalized de-duplication behavior; punctuation, arrows, operators, pluralization, possessives, or containment alone SHALL NOT carry the distinction.

#### `concept`

- `conceptKind` SHALL be one of `person`, `place`, `thing`, or `event`.
- Each item SHALL contain 2–4 clues ordered broad to specific.
- No clue SHALL name the answer or an obvious cognate.
- A playable cluster SHALL contain at least six plausibly confusable concepts of the same kind in the same part.

#### `procedure`

- Used only for a genuinely ordered process.
- Steps SHALL be atomic, correctly ordered, and safe.
- A procedure SHALL include warnings or prerequisites when omitting them could cause harm.

#### `comparison`

- Used only for a meaningful correct-versus-incorrect or A-versus-B distinction.
- Captions and visuals SHALL make the intended distinction observable without introducing irrelevant differences.
- An explanation SHOULD identify the diagnostic feature.

#### `trueFalse` and `cloze`

- SHALL be derived by default, not freely authored.
- SHALL retain `sourceItemId`, `sourceClaimIds`, and originating part in the derivation ledger even if those fields are not emitted into the consumer JSON.

#### Unsupported shapes

- `video` and `sentence` SHALL NOT be emitted. Their historical type definitions do not make them accepted live shapes.

### FR-F05: Construct optional mastery data

When objectives are enabled:

- objectives SHALL use observable verbs and remain within one lesson;
- demonstrations SHALL reference valid items and define a defensible `requiredCorrect` threshold;
- objective tests SHALL contain 5–10 MCQs, reuse strong existing MCQs first, and cover the objective rather than merely repeat one fact;
- passing policy SHOULD be approximately 80%, retryable, unless the product specifies otherwise.

## 8.7 Phase G — Visual planning and image sourcing

### FR-G01: Add images for instructional value

The visual planner SHALL classify each opportunity as:

- essential to identification or comparison;
- strongly explanatory;
- motivational or contextual;
- decorative only; or
- unsuitable for an image.

Essential and strongly explanatory opportunities receive priority. Decorative coverage SHALL NOT be used as a vanity metric.

### FR-G02: Choose the correct visual kind

- Use **photo** for real people, places, objects, species, and contextual scenes.
- Use **diagram** for structure, mechanisms, processes, controlled comparisons, and safety-critical distinctions.
- Use **map** for spatial relationships.
- Use **chart** for quantities where comparison is the lesson.
- Use **scrapbook** sparingly for an image-led overview.

### FR-G03: Use a stock-first sourcing cascade

The default order SHALL be reputable open or commercial stock providers with acceptable redistribution terms, then Wikimedia/Openverse or authoritative public-domain collections, then first-party creation or AI generation. Provider order MAY vary by subject and rights requirements.

### FR-G04: Enforce rights and attribution

Every shipped third-party image SHALL have:

- a license compatible with distribution;
- exact creator/provider attribution;
- a link to the exact source page;
- a preserved ledger record;
- item-level `illustration.credit` and `illustration.creditUrl` where applicable.

AI-generated and first-party assets SHALL record generator/tool, model or source, generation date, prompt hash, and an explicit credit. Unknown provenance is a hard release failure. When rights are unclear, the pipeline SHALL omit the image.

### FR-G05: Prevent unwanted duplication

The pipeline SHALL compute exact checksums and SHOULD compute perceptual hashes. An image SHALL not be reused across cards unless reuse is intentional, approved, and instructionally justified.

### FR-G06: Perform visual semantic QA

Every accepted image SHALL be checked for:

- relevance to the exact item;
- factual correctness and anachronisms;
- correct person, place, species, object, diagram labels, or configuration;
- absence of watermarks and unexpected text;
- absence of disallowed logos, likenesses, or unsafe content;
- adequate crop, contrast, and resolution;
- consistency between image, alt text, caption, and answer key.

### FR-G07: Require accessibility text

Alt text SHALL describe the image's relevant content without leaking a quiz answer when the image appears in an assessment context. It SHALL not begin with redundant phrases such as “image of.”

## 8.8 Phase H — Deterministic derivation

### FR-H01: Derive only from approved seeds

Derived items SHALL be created after authored items and guide claims are approved.

### FR-H02: Preserve lineage

Every derived item SHALL record:

- source item ID;
- claim IDs;
- derivation rule and version;
- originating part;
- input and output hash;
- any curated distractor set;
- later repair history.

### FR-H03: Derive `cloze` safely

- The blank SHALL be a key concept, proper noun, year, quantity, or deliberately taught value.
- The template SHALL contain exactly one `___` marker at release, even if the base schema only checks for at least one.
- The answer SHALL not remain visible elsewhere in the template.
- Function words, scaffolding words, generic verbs, and grammar-only blanks SHALL be rejected.
- Distractors SHALL be the same semantic category and grammatical form as the answer.

### FR-H04: Derive `trueFalse` safely

- False statements SHALL change one meaningful proposition, not use trivial negation or ambiguous wording.
- Each item SHALL include a clear `why` explanation.
- `whyOptions`, when present, SHALL be category-coherent, distinct, and correctly indexed.
- The distribution of `isTrue` SHOULD remain balanced enough to prevent strategy by prior probability; target 40–60% true at pack level unless content constraints justify otherwise.

### FR-H05: Re-home derived content

Derived items SHALL be placed in the source seed's part. If a seed appears in multiple parts, the canonical originating part SHALL be recorded and deliberate review reuse MAY reference the same item elsewhere.

## 8.9 Phase I — Validation and semantic review

Validation SHALL run in layers. A later layer SHALL NOT erase or hide an earlier failure.

### Layer 1: Parse and consumer-schema validation

Hard failures include invalid JSON, unsupported shapes, field-length violations, invalid enums, invalid option indices, duplicate item IDs, unresolved links, unresolved part item IDs, or invalid objective/demonstration references.

### Layer 2: File and structural integrity

The validator SHALL check:

- every declared guide path exists;
- every real part has a guide section and matching slug;
- exactly one guide `##` maps to each part;
- no orphan item exists unless explicitly classified as runtime-only;
- no synthetic `::` bank is published as authored curriculum;
- ordering values are unique or deterministically resolved;
- all relative asset paths exist and remain inside the pack folder;
- pack and asset checksums are stable.

### Layer 3: Deterministic content integrity

Hard failures include:

- answer-in-clue leaks for MCQ, concept, cloze, and pair interactions;
- duplicate or runtime-colliding MCQ options;
- multiple or missing cloze blank markers;
- degenerate cloze answers;
- invalid numeric values or non-finite numbers;
- duplicate concept names inside a playable cluster;
- true/false follow-up index errors;
- unsupported `video` or `sentence` items.

### Layer 4: Provenance and rights

Hard failures include:

- unsupported guide claims;
- missing source coverage for high-risk claims;
- shipped third-party images without credit, source URL, or permitted license;
- generated assets without recorded generator provenance;
- broken or unresolved source and asset URLs at verification time, subject to an approved offline-source policy.

### Layer 5: Coverage, ratios, and playability

The analyzer SHALL compute all metrics in Section 9 and classify each result as pass, warning, conditional exception, or hard failure.

### Layer 6: Independent semantic judge

The semantic judge SHALL evaluate:

- answer correctness;
- factual consistency with evidence and guide;
- guide-to-item alignment;
- distractor plausibility and category coherence;
- ambiguity and multiple-valid-answer risk;
- concept clue progression;
- numeric context and comparability;
- procedure ordering and safety;
- visual correctness and relevance;
- redundancy, triviality, and pedagogical value;
- reading level, tone, bias, and cultural sensitivity.

The judge SHALL output structured findings with severity, confidence, rationale, affected IDs, evidence references, and suggested repair. It SHALL NOT directly rewrite the pack.

### Layer 7: Skeptic confirmation

All semantic findings that would block release or delete content SHOULD be rechecked independently. The skeptic SHALL return `confirmed`, `rejected`, or `uncertain`, citing evidence. Only confirmed or policy-mandated uncertain findings block automated release.

### Layer 8: Rendering and human review

The pipeline SHALL produce a review surface showing:

- pack metadata and curriculum outline;
- study guide beside its part items;
- item previews by shape;
- image, attribution, alt text, and source together;
- evidence trace for each item;
- shape and part metrics;
- validation findings and patches;
- waivers and remaining risks.

The reviewer SHALL be able to approve, reject, edit, waive, or request regeneration at item, part, lesson, and pack level.

## 8.10 Phase J — Packaging and release

### FR-J01: Create a reproducible release candidate

Packaging SHALL use only approved, hashed artifacts. The pipeline SHALL write to a staging path and atomically promote the completed candidate.

### FR-J02: Bump versions intentionally

- Patch: corrections, source repairs, image replacements, or wording changes without curriculum impact.
- Minor: added parts, items, objectives, or material guide expansion.
- Major: incompatible schema or curriculum contract changes.

The exact policy MAY be configured, but every bump SHALL have a generated change summary.

### FR-J03: Revalidate the packaged form

All hard gates SHALL run against the exact packaged artifact, not only intermediate files.

### FR-J04: Emit a release report

The release report SHALL include:

- final status and pack version;
- schema version;
- item, lesson, part, guide-word, source, and image counts;
- hard-gate results;
- target-band results and waivers;
- semantic judge and skeptic summary;
- change summary;
- checksums and publication destination;
- residual risks and recommended review date.

---

## 9. Ratios, thresholds, and analyzed metrics

Ratios SHALL be calculated over unique final items unless a metric explicitly says “item references.” Synthetic parts and deprecated/draft packs SHALL be excluded from release-health rollups.

## 9.1 Hard release requirements

| Metric | Requirement |
|---|---:|
| Consumer schema errors | 0 |
| Unsupported live shapes (`video`, `sentence`) | 0 |
| Duplicate item IDs | 0 |
| Broken item, link, objective, or demonstration references | 0 |
| Missing lesson guide paths/files | 0 |
| Parts with fewer than 3 final items (`thin`) | 0 |
| Parts with facts but zero playable item shapes (`barren`) | 0 |
| Parts with no `mcq`, `trueFalse`, or `cloze` (`noQuiz`) | 0 |
| Parts with fewer than 2 game shapes (`underShaped`) | 0, unless waived for a justified special-purpose part |
| Unsupported material guide claims | 0 |
| Answer-in-clue leaks | 0 |
| Duplicate/runtime-colliding MCQ options | 0 |
| Degenerate or malformed cloze items | 0 |
| Unattributed or unlicensed shipped third-party images | 0 |
| Generated assets without provenance | 0 |
| Confirmed broken semantic findings | 0 |
| `trueFalse` share | ≤33.3% of the pack and not the plurality shape |
| Single-shape dominance | No shape ≥45% without an approved topic-flex waiver |

## 9.2 Default quality targets

These are planning bands, not permission to force irrelevant items.

| Shape or structure | Default target |
|---|---|
| `fact` | 12–20% of pack; at least 3 per part |
| `pair` | 10–20% of pack; cluster at least 6 when part-scoped matching requires it |
| `definition` | 5–12% where the topic teaches named terms |
| `numeric` | 5–12% for quantitative topics; at least 6 comparable-unit items per playable cluster |
| authored `mcq` | 3–8% of pack and at least 1 per part where feasible |
| `concept` | 4–8% when the topic has confusable entities; at least 6 of the same `conceptKind` per playable part |
| derived `cloze` | 3–8% |
| derived `trueFalse` | Enough for variety, capped at one-third; never hand-authored by default |
| `procedure` | 0–5%; up to approximately 15% for genuine how-to topics |
| `comparison` | At least 3 when a real visual A/B distinction exists; otherwise 0 is acceptable |
| Live-shape breadth | Target all 10; minimum 8 when topic-flex exclusions are documented |
| Part size | Prefer 6–10 final item references; larger clusters require a playability reason |
| Authored game-shaped seeds | 3–5 per part across 2–3 shapes |
| Generative retrieval | At least 1 of pair, definition, numeric, or cloze per part |
| Elaborative retrieval | At least 1 of explained MCQ, concept, comparison, procedure, or explained true/false per part |
| Lesson size | Approximately 2–4 parts |
| Guide size | Approximately 600–1,500 words per lesson |
| Local quiz alignment | At least 90% of a part-triggered quiz should be drawable from the same part before any pack-level top-up |

## 9.3 Topic-flex rules

The analyzer SHALL apply these rules before raising ratio failures:

- `numeric` may be zero for non-quantitative subjects and exceed 12% for explicitly quantitative packs.
- `procedure` may be zero unless there is a genuinely ordered process.
- `comparison` may be zero unless a precise distinction can be taught.
- `concept` may be omitted when the topic lacks a six-item confusable set.
- `definition` may be low in pure recognition or vocabulary packs where `pair` better serves the task.
- Group-game minimums are conditional: if a shape is emitted for a group game, the minimum becomes mandatory.

Each deviation SHALL have a machine-readable reason code, free-text rationale, and approving actor when it crosses a hard threshold.

## 9.4 Required computed metrics

### Structure

- lesson count, part count, unique item count, and item-reference count;
- parts per lesson; items and shapes per part;
- orphan items, duplicate references, thin parts, oversized parts;
- guide-path and anchor coverage;
- guide words per lesson and section;
- bolded-term coverage by items.

### Shape mix

For each shape `s`:

`shape_share(s) = unique_items_of_shape_s / total_unique_items`

Also compute authored versus derived share, pack plurality shape, live-shape breadth, and per-part shape breadth.

### Cohesion

- `fact_retrieval_link_rate = facts_with_same_part_retrieval / facts`
- `item_guide_trace_rate = items_traced_to_guide_claim / items`
- `derived_home_rate = derived_items_in_origin_part / derived_items`
- `local_quiz_pool_rate = eligible_same_part_quiz_items / required_round_items`, capped at 1.0
- `anchor_match_rate = parts_with_matching_guide_heading / real_parts`

Targets for the first three trace metrics and anchor match rate: `1.00`.

### Evidence

- material claims by confidence and source class;
- unsupported, single-source, contradicted, stale, and time-sensitive claims;
- independent source groups per high-risk claim;
- guide claim coverage and item claim coverage;
- numeric claims missing units, periods, or population/geography.

### Assessment quality

- MCQs with four options;
- duplicate and near-duplicate options;
- explanation coverage;
- category-coherence judge pass rate;
- answer-position distribution;
- `trueFalse` truth-value distribution;
- cloze answer-category coherence;
- confirmed ambiguous or broken items;
- objective-to-item and objective-test coverage when enabled.

Answer positions SHOULD not exhibit a strong exploitable skew. As a diagnostic default, warn when any one MCQ answer position exceeds 35% once the pack contains at least 20 MCQs. Do not mechanically reorder options if order has semantic meaning.

### Images

- total images and image-bearing item share;
- images by kind and provider;
- licensed, attributed, generated, rejected, duplicate, and broken counts;
- exact/perceptual duplication rate;
- alt-text coverage;
- visual semantic-review pass rate;
- essential visual opportunities fulfilled.

The release requirement is 100% attribution/provenance and alt-text coverage for shipped images, not a minimum image-bearing item percentage.

### Operational

- stage latency, retries, tool failures, and cache-hit rate;
- tokens and cost per approved item and per pack;
- first-pass acceptance rate by artifact type;
- repair count and patch churn;
- human review time;
- failure counts by requirement ID;
- model and prompt version comparison.

---

## 10. Error handling, repair, and retry behavior

### 10.1 Typed failures

Every failure SHALL have:

- stable error code;
- requirement ID;
- severity;
- stage and artifact ID;
- deterministic or semantic classification;
- evidence and reproducible check;
- retryability;
- suggested earliest repair stage;
- human-review requirement.

### 10.2 Retry policy

- Network and rate-limit failures MAY be retried with exponential backoff and jitter.
- Invalid structured LLM output MAY be retried with validation errors and the smallest necessary context.
- A semantic failure SHALL trigger targeted repair, not blind regeneration of the whole pack.
- The same failed generation SHALL not be retried indefinitely. After a configurable limit, escalate or choose a deterministic fallback.
- Image sourcing failure SHALL fall back to another provider, first-party generation, or text-only rendering; it SHALL never fall back to an unlicensed image.

### 10.3 Repair scope

Repairs SHOULD operate at the smallest stable unit:

1. field;
2. item;
3. part;
4. guide section;
5. lesson;
6. pack only when structure is fundamentally wrong.

Any repair SHALL rerun all dependent checks. Factual repairs SHALL rerun evidence alignment, guide-to-item alignment, and affected semantic judges.

---

## 11. Human-in-the-loop policy

### 11.1 Mandatory human checkpoints

Human approval SHALL be required for:

- high-stakes health, safety, legal, financial, or regulated content;
- requester-specific or confidential source material;
- disputed claims retained in the guide;
- living-person likenesses or sensitive historical imagery;
- branded or trademark-sensitive assets;
- any waiver of a hard release threshold;
- schema-capability gaps;
- the first production release of a new pipeline or major prompt/model version.

### 11.2 Recommended checkpoints

The default workflow SHOULD request human approval for:

- the clarified brief;
- the curriculum plan for large packs;
- the guide and a representative part before scaling item generation;
- flagged or generated images;
- the final release candidate.

### 11.3 Approval durability

An approval SHALL bind to artifact hashes. A material change invalidates the approval; editorial changes MAY preserve it according to configured policy.

---

## 12. LLM execution requirements

### 12.1 Structured output

All machine-consumed LLM responses SHALL conform to a stage-specific JSON Schema. Free-form prose MAY be included only in designated fields.

### 12.2 Context minimization

Each role SHALL receive the minimum trusted context required. The pipeline SHOULD process one guide section or part per authoring call to reduce cross-part leakage and improve repair locality.

### 12.3 Temperature and reproducibility

- Research extraction and judging SHOULD use low-variance settings.
- Creative wording and visual prompts MAY use moderate variance.
- Seeds, prompt versions, model identifiers, and parameters SHALL be recorded.
- Exact byte-for-byte reproducibility from an LLM is not assumed; artifact hashes and approval history provide release reproducibility.

### 12.4 Confidence is not evidence

Model-reported confidence SHALL never substitute for source support or judge agreement.

### 12.5 Cost controls

The orchestrator SHALL support per-run budgets for tokens, searches, generated images, and semantic reviews. Budget exhaustion SHALL pause or downgrade optional work, never skip a hard gate.

### 12.6 Model changes

A new model or materially changed prompt SHALL be evaluated against a fixed benchmark set containing:

- clear and ambiguous ideas;
- quantitative, historical, scientific, vocabulary, and procedural topics;
- difficult MCQ distractor cases;
- source contradictions;
- image-rights failures;
- answer leaks and runtime option collisions;
- topics that legitimately omit optional shapes.

---

## 13. Security, privacy, and compliance

- Secrets SHALL remain in the tool layer and SHALL never be included in LLM prompts, run artifacts, or logs.
- Requester identity and private attachments SHALL be minimized and access-controlled.
- External content SHALL be treated as untrusted input.
- Downloaded files SHALL be type-checked, size-limited, malware-scanned where appropriate, and stored outside publishable paths until accepted.
- Source and image URLs SHALL use allowed protocols and prevent path traversal or internal-network access.
- The system SHALL respect provider terms, rate limits, robots policies where applicable, and license obligations.
- Logs SHALL redact credentials, private URLs, and sensitive data.
- Retention and deletion policies SHALL be configurable by project.

---

## 14. Non-functional requirements

### 14.1 Idempotence

Rerunning an unchanged successful stage SHALL reuse the prior artifact or produce a semantically equivalent artifact without duplicate IDs, assets, or references.

### 14.2 Resumability

The pipeline SHALL resume from the last valid state after interruption. Completed artifacts SHALL be addressed by content hash.

### 14.3 Concurrency

Independent parts MAY be researched, authored, illustrated, or judged concurrently after their shared dependencies are approved. The orchestrator SHALL serialize writes to shared manifests and final `pack.json` assembly.

### 14.4 Performance

The system SHALL publish stage-level latency objectives after baseline measurement. Interactive interview turns SHOULD return promptly; long research and image operations SHALL surface progress and remain cancellable.

### 14.5 Observability

Every stage SHALL emit structured events for start, progress, artifact creation, validation, repair, approval, cost, and completion. A run dashboard SHOULD expose the critical path and outstanding blockers.

### 14.6 Portability

Intermediate artifacts SHALL use documented JSON/NDJSON/Markdown formats and avoid provider-specific hidden state. Provider adapters SHALL normalize search results, citations, and image rights into pipeline schemas.

### 14.7 Accessibility

Generated text, images, and review surfaces SHALL support accessible reading order, alt text, sufficient contrast, keyboard review, and non-image fallbacks.

---

## 15. Acceptance criteria

The pipeline is ready for production use when it can demonstrate the following on an agreed benchmark set:

1. An ambiguous idea triggers a concise interview and produces an approved brief.
2. A well-specified idea proceeds without unnecessary questions and records its assumptions.
3. Every material guide claim traces to evidence; unsupported claims block release.
4. A final pack validates against the exact pinned consumer schema.
5. Every real part maps to one guide section, has at least three items, has at least two game shapes, and has quiz content.
6. Derived items retain lineage and remain in their source parts.
7. Shape ratios and topic-flex exceptions are correctly computed and reported.
8. MCQ answer leaks, duplicate/runtime-colliding options, incoherent distractors, and ambiguous keys are detected.
9. Degenerate cloze items and low-value true/false transformations are rejected.
10. Every shipped image has rights, provenance, attribution, alt text, and semantic visual approval.
11. A failed item can be repaired without regenerating unrelated lessons or parts.
12. A stopped run resumes without duplicate artifacts or lost approvals.
13. The packaged artifact is revalidated and its checksums match the release report.
14. Human reviewers can trace any card back to its guide claim, source, generation event, and validation history.
15. A model or prompt regression is detectable on the benchmark before rollout.

---

## 16. Suggested implementation sequence

### Milestone 1 — Deterministic foundation

- Implement run state, manifests, exact schema pinning, pack assembly, stable IDs, file checks, structural validation, and metrics.
- Reuse the repository's current validator, dashboard analysis, derivation scripts, and content-integrity tests where possible.

### Milestone 2 — Brief, research, and guide pipeline

- Add triage, bounded interview, evidence ledger, curriculum plan, guide generation, claim coverage, and human approval.

### Milestone 3 — Item authoring and semantic QA

- Add part-scoped item generation, deterministic derivation, semantic judge, skeptic confirmation, and targeted repair.

### Milestone 4 — Visual pipeline

- Add visual planning, provider adapters, rights ledger, caching, de-duplication, visual QA, and accessibility checks.

### Milestone 5 — Release automation and evaluation

- Add review UI, waivers, atomic packaging, publishing adapter, benchmark suite, model/prompt canaries, and operational dashboards.

---

## 17. Decisions to resolve before implementation

The following should become configuration or explicit product decisions:

1. Which briefs may be auto-approved versus requiring requester confirmation?
2. Which domains are classified as high stakes?
3. Which research providers and source types are permitted?
4. Is card-level content provenance mandatory for every item, or may lesson-level sources remain a fallback?
5. Should `underShaped = 0` be a hard gate for every production pack or a waivable quality gate?
6. What final part-size ceiling applies to valid six-item `concept` or `numeric` clusters plus teaching facts?
7. Which image licenses are accepted, and may remote stock URLs ship or must every asset be cached?
8. Which semantic findings require skeptic confirmation?
9. Which stages require human approval by risk tier?
10. What token, search, image, latency, and cost budgets apply by pack size?
11. What publication destinations and rollback mechanism are required?
12. What is the retention policy for source excerpts, private inputs, LLM prompts, and generated assets?

---

## 18. Repository alignment

This specification builds on the current durable standards and tooling:

- [`KNOWLEDGE_PACKS.md`](references/KNOWLEDGE_PACKS.md) — canonical authoring model and item fields;
- [`SHAPES.md`](references/SHAPES.md) — live shapes, shape targets, guide structure, and visual fields;
- [`AUDIT.md`](references/AUDIT.md) — hard validation, part-health metrics, and semantic-quality model;
- [`PROVENANCE.md`](references/PROVENANCE.md) — image rights, attribution, caching, and provenance;
- [`REWORK.md`](references/REWORK.md) — historical feedback and the rationale for shape balance and part coherence;
- `@flashfeed/pack-schema` — the versioned consumer contract;
- `tools/validate.ts` — current parse, schema, attribution, answer-leak, and MCQ-integrity gate;
- `tools/contentQualityChecks.ts` — deterministic content-quality checks;
- `tools/judge-content.wf.js` — semantic judge pattern;
- `scripts/derive-content.mjs` — deterministic derived-content pattern;
- `tools/build-dashboard.ts` — cross-pack and part-level analysis.

Where this document proposes a stronger future gate than the current repository enforces, the stronger behavior is stated as a pipeline requirement and should be implemented incrementally with a benchmark and migration report.
