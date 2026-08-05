"""Pipeline artifact models and structured-output contracts."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field, model_validator


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


class StrictModel(BaseModel):
    model_config = {"extra": "forbid"}


class ClarificationQuestion(StrictModel):
    question_id: str
    question: str
    why_it_matters: str
    required: bool = True


class BriefDraft(StrictModel):
    working_title: str
    pack_id: str
    idea_summary: str
    target_audience: str
    assumed_prior_knowledge: str
    language: str = "en"
    locale: str = "en-US"
    reading_level: str
    learning_outcomes: list[str]
    included_topics: list[str]
    excluded_topics: list[str]
    depth: Literal["overview", "practical", "deep"]
    tone: str
    time_sensitivity: Literal["low", "medium", "high"]
    as_of_date: str
    risk_classification: Literal["general", "sensitive", "high-stakes"]
    source_constraints: list[str]
    image_preferences: list[str]
    acceptance_criteria: list[str]
    unresolved_assumptions: list[str]
    clarification_questions: list[ClarificationQuestion]


class ApprovedBrief(BriefDraft):
    requester_answers: dict[str, str] = Field(default_factory=dict)
    requester_approved: bool = False
    approved_at: str | None = None


class ResearchSource(StrictModel):
    source_id: str
    title: str
    url: str
    author_or_institution: str = "Unknown"
    publication_date: str | None = None
    retrieved_at: str
    source_type: Literal["primary", "secondary", "tertiary", "requester-provided"]
    query: str | None = None


class ResearchDossier(StrictModel):
    topic: str
    report_markdown: str
    queries: list[str]
    sources: list[ResearchSource]
    provided_files: list[str]
    unresolved_questions: list[str]
    response_id: str | None = None
    mock: bool = False


class ClaimSupport(StrictModel):
    source_id: str
    support_summary: str
    locator: str | None = None


class EvidenceClaim(StrictModel):
    claim_id: str
    claim: str
    topic: str
    proposed_lesson: str
    proposed_part: str
    claim_type: Literal[
        "fact",
        "definition",
        "quantity",
        "chronology",
        "causation",
        "procedure",
        "opinion",
        "controversy",
        "safety-warning",
    ]
    support: list[ClaimSupport]
    agreement: Literal["single-source", "corroborated", "conflicted", "unknown"]
    confidence: Literal["high", "medium", "low", "disputed"]
    time_sensitivity: Literal["low", "medium", "high"]
    allowed_uses: list[Literal["guide", "answer-key", "numeric", "image-caption", "background"]]
    approved_for_instruction: bool
    human_review_required: bool


class EvidenceLedger(StrictModel):
    topic: str
    claims: list[EvidenceClaim]
    research_gaps: list[str]
    extraction_notes: list[str]


class PartPlan(StrictModel):
    part_id: str
    title: str
    objective: str
    guide_heading: str
    guide_anchor: str
    claim_ids: list[str]
    planned_shapes: list[Literal["fact", "definition", "pair", "mcq", "numeric", "procedure"]]
    visual_opportunities: list[str]


class LessonPlan(StrictModel):
    lesson_id: str
    title: str
    rationale: str
    parts: list[PartPlan]


class PackDesign(StrictModel):
    pack_id: str
    pack_name: str
    description: str
    target_item_count: int
    target_shape_ratios: dict[str, float]
    lessons: list[LessonPlan]
    coverage_gaps: list[str]
    topic_flex_exclusions: list[str]


class ItemDraft(StrictModel):
    item_id: str
    part_id: str
    claim_ids: list[str]
    shape: Literal["fact", "definition", "pair", "mcq", "numeric", "procedure"]
    tags: list[str]
    title: str | None = None
    body: str | None = None
    term: str | None = None
    definition: str | None = None
    side_a: str | None = None
    side_b: str | None = None
    prompt: str | None = None
    options: list[str] | None = None
    correct_index: int | None = None
    explanation: str | None = None
    numeric_value: float | None = None
    unit: str | None = None
    tolerance: float | None = None
    goal: str | None = None
    steps: list[str] | None = None
    notes: str | None = None

    @model_validator(mode="after")
    def validate_shape_fields(self) -> ItemDraft:
        required: dict[str, tuple[str, ...]] = {
            "fact": ("title", "body"),
            "definition": ("term", "definition"),
            "pair": ("side_a", "side_b"),
            "mcq": ("prompt", "options", "correct_index"),
            "numeric": ("prompt", "numeric_value"),
            "procedure": ("goal", "steps"),
        }
        missing = [name for name in required[self.shape] if getattr(self, name) is None]
        if missing:
            raise ValueError(f"{self.shape} item is missing: {', '.join(missing)}")
        if self.shape == "mcq":
            assert self.options is not None and self.correct_index is not None
            if not 2 <= len(self.options) <= 4:
                raise ValueError("MCQs require 2-4 options")
            if not 0 <= self.correct_index < len(self.options):
                raise ValueError("MCQ correct_index is out of range")
        if self.shape == "procedure" and self.steps is not None and len(self.steps) < 2:
            raise ValueError("Procedures require at least two steps")
        return self


class AuthoredItems(StrictModel):
    items: list[ItemDraft]
    author_notes: list[str]


class VisualBrief(StrictModel):
    asset_id: str
    item_id: str
    teaching_purpose: str
    kind: Literal["photo", "diagram", "map", "chart", "scrapbook"]
    prompt: str
    search_term: str
    alt_text: str
    generate: bool


class VisualPlan(StrictModel):
    briefs: list[VisualBrief]
    exclusions: list[str]


class ReviewFinding(StrictModel):
    severity: Literal["error", "warning", "note"]
    artifact_id: str
    issue: str
    recommendation: str


class SemanticReview(StrictModel):
    passed: bool
    findings: list[ReviewFinding]
    summary: str


class ValidationIssue(StrictModel):
    severity: Literal["error", "warning", "note"]
    code: str
    path: str
    message: str


class ValidationMetrics(StrictModel):
    item_count: int
    shape_counts: dict[str, int]
    shape_ratios: dict[str, float]
    evidence_coverage: float
    part_assignment_coverage: float
    visual_provenance_coverage: float
    source_count: int


class ValidationReport(StrictModel):
    validated_at: str
    schema_version: str
    hard_gates_passed: bool
    publishable: bool
    mock_run: bool
    issues: list[ValidationIssue]
    metrics: ValidationMetrics


class StageState(str, Enum):
    NOT_STARTED = "not_started"
    RUNNING = "running"
    WAITING_APPROVAL = "waiting_approval"
    COMPLETE = "complete"
    FAILED = "failed"
    STALE = "stale"


class ArtifactRecord(StrictModel):
    name: str
    relative_path: str
    sha256: str
    created_at: str
    producer: str
    input_hashes: list[str]


class AgentCallRecord(StrictModel):
    stage: str
    agent: str
    model: str
    credential_profile: str
    response_id: str | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    tool_calls: int = 0
    created_at: str


class RunManifest(StrictModel):
    run_id: str
    created_at: str
    updated_at: str
    status: str
    pipeline_version: str
    schema_version: str
    provider: str
    mock: bool
    stages: dict[str, StageState]
    artifacts: dict[str, ArtifactRecord]
    agent_calls: list[AgentCallRecord]
    final_pack_id: str | None = None
    final_bundle_path: str | None = None
