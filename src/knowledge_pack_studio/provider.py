"""OpenAI and deterministic mock providers for logical specialist agents."""

from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
from pathlib import Path
from typing import Any, Protocol, TypeVar
from urllib.parse import urlparse

from pydantic import BaseModel

from . import prompts
from .config import StudioConfig
from .models import (
    AgentCallRecord,
    ApprovedBrief,
    AuthoredItems,
    BriefDraft,
    ClaimSupport,
    EvidenceClaim,
    EvidenceLedger,
    ItemDraft,
    LessonPlan,
    PackDesign,
    PartPlan,
    ResearchDossier,
    ResearchSource,
    SemanticReview,
    VisualBrief,
    VisualPlan,
    utc_now,
)

T = TypeVar("T", bound=BaseModel)


class PipelineProvider(Protocol):
    mock: bool

    def clarify(self, idea: str, intake: dict[str, Any]) -> tuple[BriefDraft, AgentCallRecord]: ...

    def research(
        self,
        brief: ApprovedBrief,
        source_urls: list[str],
        file_paths: list[Path],
    ) -> tuple[ResearchDossier, AgentCallRecord]: ...

    def extract(
        self, brief: ApprovedBrief, dossier: ResearchDossier
    ) -> tuple[EvidenceLedger, AgentCallRecord]: ...

    def write_guide(
        self, brief: ApprovedBrief, ledger: EvidenceLedger
    ) -> tuple[str, AgentCallRecord]: ...

    def design(
        self, brief: ApprovedBrief, ledger: EvidenceLedger, guide: str
    ) -> tuple[PackDesign, AgentCallRecord]: ...

    def author(
        self,
        brief: ApprovedBrief,
        ledger: EvidenceLedger,
        guide: str,
        design: PackDesign,
    ) -> tuple[AuthoredItems, AgentCallRecord]: ...

    def plan_visuals(
        self,
        ledger: EvidenceLedger,
        design: PackDesign,
        items: AuthoredItems,
    ) -> tuple[VisualPlan, AgentCallRecord]: ...

    def review(
        self,
        ledger: EvidenceLedger,
        guide: str,
        design: PackDesign,
        items: AuthoredItems,
    ) -> tuple[SemanticReview, AgentCallRecord]: ...

    def generate_image(self, prompt: str) -> bytes: ...


class OpenAIProvider:
    mock = False

    def __init__(self, config: StudioConfig, credentials: dict[str, str]):
        self.config = config
        self.credentials = credentials

    def _client(self, agent_name: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise RuntimeError("Install the project dependencies before using OpenAI") from exc
        profile = self.config.agents[agent_name].credential
        key = self.credentials.get(profile) or self.credentials.get("default")
        if not key:
            raise RuntimeError(f"No API key is configured for credential profile '{profile}'")
        return OpenAI(api_key=key)

    def _parsed(
        self,
        agent_name: str,
        system: str,
        user: str,
        output_model: type[T],
    ) -> tuple[T, AgentCallRecord]:
        agent = self.config.agents[agent_name]
        response = self._client(agent_name).responses.parse(
            model=agent.model,
            reasoning={"effort": agent.reasoning_effort},
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            text_format=output_model,
            store=False,
        )
        if response.output_parsed is None:
            raise RuntimeError(f"{agent_name} returned no structured output")
        return response.output_parsed, self._call_record(agent_name, response)

    def _text(self, agent_name: str, system: str, user: str) -> tuple[str, AgentCallRecord]:
        agent = self.config.agents[agent_name]
        response = self._client(agent_name).responses.create(
            model=agent.model,
            reasoning={"effort": agent.reasoning_effort},
            input=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            store=False,
        )
        if not response.output_text:
            raise RuntimeError(f"{agent_name} returned no text")
        return response.output_text, self._call_record(agent_name, response)

    def _call_record(self, agent_name: str, response: Any) -> AgentCallRecord:
        agent = self.config.agents[agent_name]
        usage = getattr(response, "usage", None)
        output = getattr(response, "output", []) or []
        return AgentCallRecord(
            stage=agent_name,
            agent=agent_name,
            model=agent.model,
            credential_profile=agent.credential,
            response_id=getattr(response, "id", None),
            input_tokens=getattr(usage, "input_tokens", None),
            output_tokens=getattr(usage, "output_tokens", None),
            tool_calls=sum(
                1 for item in output if str(getattr(item, "type", "")).endswith("_call")
            ),
            created_at=utc_now(),
        )

    def clarify(self, idea: str, intake: dict[str, Any]) -> tuple[BriefDraft, AgentCallRecord]:
        return self._parsed(
            "clarifier",
            prompts.CLARIFIER,
            json.dumps({"idea": idea, "intake": intake}, indent=2),
            BriefDraft,
        )

    def research(
        self,
        brief: ApprovedBrief,
        source_urls: list[str],
        file_paths: list[Path],
    ) -> tuple[ResearchDossier, AgentCallRecord]:
        agent_name = "researcher"
        agent = self.config.agents[agent_name]
        content: list[dict[str, Any]] = [
            {
                "type": "input_text",
                "text": json.dumps(
                    {
                        "approved_brief": brief.model_dump(mode="json"),
                        "requester_urls": source_urls,
                        "search_budget": self.config.max_web_searches,
                    },
                    indent=2,
                ),
            }
        ]
        for path in file_paths:
            mime = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
            encoded = base64.b64encode(path.read_bytes()).decode("ascii")
            content.append(
                {
                    "type": "input_file",
                    "filename": path.name,
                    "file_data": f"data:{mime};base64,{encoded}",
                }
            )
        response = self._client(agent_name).responses.create(
            model=agent.model,
            reasoning={"effort": agent.reasoning_effort},
            tools=[{"type": "web_search"}],
            include=["web_search_call.action.sources"],
            max_tool_calls=self.config.max_web_searches,
            input=[
                {"role": "system", "content": prompts.RESEARCHER},
                {"role": "user", "content": content},
            ],
            store=False,
        )
        raw = response.model_dump(mode="json")
        queries: list[str] = []
        source_rows: dict[str, dict[str, str]] = {}
        for item in raw.get("output", []):
            if item.get("type") == "web_search_call":
                action = item.get("action") or {}
                query = action.get("query")
                if query and query not in queries:
                    queries.append(query)
                for source in action.get("sources") or []:
                    url = source.get("url")
                    if url:
                        source_rows[url] = {
                            "title": source.get("title") or url,
                            "query": query or "",
                        }
            if item.get("type") == "message":
                for part in item.get("content") or []:
                    for annotation in part.get("annotations") or []:
                        url = annotation.get("url")
                        if url:
                            source_rows[url] = {
                                "title": annotation.get("title") or url,
                                "query": "",
                            }
        sources = []
        for url, row in source_rows.items():
            host = urlparse(url).netloc.removeprefix("www.") or "Unknown"
            source_id = "src-" + hashlib.sha256(url.encode()).hexdigest()[:10]
            sources.append(
                ResearchSource(
                    source_id=source_id,
                    title=row["title"],
                    url=url,
                    author_or_institution=host,
                    retrieved_at=utc_now(),
                    source_type="secondary",
                    query=row["query"] or None,
                )
            )
        dossier = ResearchDossier(
            topic=brief.working_title,
            report_markdown=response.output_text,
            queries=queries,
            sources=sources,
            provided_files=[path.name for path in file_paths],
            unresolved_questions=[],
            response_id=getattr(response, "id", None),
        )
        return dossier, self._call_record(agent_name, response)

    def extract(
        self, brief: ApprovedBrief, dossier: ResearchDossier
    ) -> tuple[EvidenceLedger, AgentCallRecord]:
        return self._parsed(
            "extractor",
            prompts.EXTRACTOR,
            json.dumps(
                {
                    "brief": brief.model_dump(mode="json"),
                    "dossier": dossier.model_dump(mode="json"),
                },
                indent=2,
            ),
            EvidenceLedger,
        )

    def write_guide(
        self, brief: ApprovedBrief, ledger: EvidenceLedger
    ) -> tuple[str, AgentCallRecord]:
        return self._text(
            "guide_author",
            prompts.GUIDE_AUTHOR,
            json.dumps(
                {"brief": brief.model_dump(mode="json"), "ledger": ledger.model_dump(mode="json")},
                indent=2,
            ),
        )

    def design(
        self, brief: ApprovedBrief, ledger: EvidenceLedger, guide: str
    ) -> tuple[PackDesign, AgentCallRecord]:
        return self._parsed(
            "pack_designer",
            prompts.PACK_DESIGNER,
            json.dumps(
                {
                    "brief": brief.model_dump(mode="json"),
                    "ledger": ledger.model_dump(mode="json"),
                    "guide_markdown": guide,
                    "target_item_count": self.config.target_item_count,
                },
                indent=2,
            ),
            PackDesign,
        )

    def author(
        self,
        brief: ApprovedBrief,
        ledger: EvidenceLedger,
        guide: str,
        design: PackDesign,
    ) -> tuple[AuthoredItems, AgentCallRecord]:
        return self._parsed(
            "item_author",
            prompts.ITEM_AUTHOR,
            json.dumps(
                {
                    "brief": brief.model_dump(mode="json"),
                    "ledger": ledger.model_dump(mode="json"),
                    "guide_markdown": guide,
                    "design": design.model_dump(mode="json"),
                },
                indent=2,
            ),
            AuthoredItems,
        )

    def plan_visuals(
        self,
        ledger: EvidenceLedger,
        design: PackDesign,
        items: AuthoredItems,
    ) -> tuple[VisualPlan, AgentCallRecord]:
        return self._parsed(
            "visual_director",
            prompts.VISUAL_DIRECTOR,
            json.dumps(
                {
                    "ledger": ledger.model_dump(mode="json"),
                    "design": design.model_dump(mode="json"),
                    "items": items.model_dump(mode="json"),
                    "image_limit": self.config.image_count_limit,
                },
                indent=2,
            ),
            VisualPlan,
        )

    def review(
        self,
        ledger: EvidenceLedger,
        guide: str,
        design: PackDesign,
        items: AuthoredItems,
    ) -> tuple[SemanticReview, AgentCallRecord]:
        return self._parsed(
            "reviewer",
            prompts.REVIEWER,
            json.dumps(
                {
                    "ledger": ledger.model_dump(mode="json"),
                    "guide_markdown": guide,
                    "design": design.model_dump(mode="json"),
                    "items": items.model_dump(mode="json"),
                },
                indent=2,
            ),
            SemanticReview,
        )

    def generate_image(self, prompt: str) -> bytes:
        client = self._client("visual_director")
        result = client.images.generate(model=self.config.image_model, prompt=prompt)
        if not result.data or not result.data[0].b64_json:
            raise RuntimeError("Image generation returned no image")
        return base64.b64decode(result.data[0].b64_json)


class MockProvider:
    """Deterministic sample provider. Its output can never pass the publishable gate."""

    mock = True

    def __init__(self, config: StudioConfig):
        self.config = config

    def _call(self, agent: str) -> AgentCallRecord:
        return AgentCallRecord(
            stage=agent,
            agent=agent,
            model="mock-deterministic",
            credential_profile="none",
            created_at=utc_now(),
        )

    def clarify(self, idea: str, intake: dict[str, Any]) -> tuple[BriefDraft, AgentCallRecord]:
        brief = BriefDraft(
            working_title="How Honey Bees Communicate — Mock Demonstration",
            pack_id="honey-bee-communication-mock",
            idea_summary=idea,
            target_audience=intake.get("audience") or "Curious adult beginners",
            assumed_prior_knowledge="None",
            reading_level="General adult",
            learning_outcomes=[
                "Explain what information the waggle dance communicates",
                "Describe Karl von Frisch's role in decoding bee communication",
            ],
            included_topics=["waggle dance", "direction", "distance", "Karl von Frisch"],
            excluded_topics=["beekeeping medical advice", "colony disease treatment"],
            depth="overview",
            tone="Clear, practical, and evidence-led",
            time_sensitivity="low",
            as_of_date=utc_now()[:10],
            risk_classification="general",
            source_constraints=["Prefer scientific and institutional sources"],
            image_preferences=["Educational diagrams rather than decorative photos"],
            acceptance_criteria=["Every item traces to an approved claim"],
            unresolved_assumptions=["Mock mode uses a bundled demonstration topic"],
            clarification_questions=[],
        )
        return brief, self._call("clarifier")

    def research(
        self,
        brief: ApprovedBrief,
        source_urls: list[str],
        file_paths: list[Path],
    ) -> tuple[ResearchDossier, AgentCallRecord]:
        sources = [
            ResearchSource(
                source_id="src-nobel",
                title="Karl von Frisch — Facts",
                url="https://www.nobelprize.org/prizes/medicine/1973/frisch/facts/",
                author_or_institution="The Nobel Prize",
                retrieved_at=utc_now(),
                source_type="primary",
            ),
            ResearchSource(
                source_id="src-britannica",
                title="Waggle dance",
                url="https://www.britannica.com/science/waggle-dance",
                author_or_institution="Encyclopaedia Britannica",
                retrieved_at=utc_now(),
                source_type="secondary",
            ),
        ]
        dossier = ResearchDossier(
            topic=brief.working_title,
            report_markdown=(
                "# Mock research dossier\n\n"
                "Honey bees use a waggle dance to communicate information about useful food "
                "sources. The dance's orientation conveys direction relative to the sun, and "
                "features of the waggle run convey distance. Karl von Frisch's behavioral "
                "research helped decode this system and contributed to the 1973 Nobel Prize.\n\n"
                "> Mock mode demonstrates the artifact flow; it is not a live research result."
            ),
            queries=["honey bee waggle dance direction distance", "Karl von Frisch Nobel 1973"],
            sources=sources,
            provided_files=[path.name for path in file_paths],
            unresolved_questions=[],
            mock=True,
        )
        return dossier, self._call("researcher")

    def extract(
        self, brief: ApprovedBrief, dossier: ResearchDossier
    ) -> tuple[EvidenceLedger, AgentCallRecord]:
        claims = [
            EvidenceClaim(
                claim_id="claim-dance-purpose",
                claim="A honey bee waggle dance communicates the direction and distance of a resource.",
                topic="waggle dance",
                proposed_lesson="Bee communication",
                proposed_part="Reading the dance",
                claim_type="fact",
                support=[
                    ClaimSupport(
                        source_id="src-britannica",
                        support_summary="Describes the dance's navigational information",
                    )
                ],
                agreement="single-source",
                confidence="high",
                time_sensitivity="low",
                allowed_uses=["guide", "answer-key", "image-caption"],
                approved_for_instruction=True,
                human_review_required=False,
            ),
            EvidenceClaim(
                claim_id="claim-angle",
                claim="The angle of the waggle run encodes direction relative to the sun's position.",
                topic="direction",
                proposed_lesson="Bee communication",
                proposed_part="Reading the dance",
                claim_type="fact",
                support=[
                    ClaimSupport(
                        source_id="src-britannica",
                        support_summary="Explains angular direction encoding",
                    )
                ],
                agreement="single-source",
                confidence="high",
                time_sensitivity="low",
                allowed_uses=["guide", "answer-key", "image-caption"],
                approved_for_instruction=True,
                human_review_required=False,
            ),
            EvidenceClaim(
                claim_id="claim-frisch",
                claim="Karl von Frisch helped decode honey bee communication and shared the 1973 Nobel Prize in Physiology or Medicine.",
                topic="history",
                proposed_lesson="Bee communication",
                proposed_part="How it was decoded",
                claim_type="chronology",
                support=[
                    ClaimSupport(
                        source_id="src-nobel",
                        support_summary="Records Frisch's work and the 1973 prize",
                    )
                ],
                agreement="single-source",
                confidence="high",
                time_sensitivity="low",
                allowed_uses=["guide", "answer-key", "numeric"],
                approved_for_instruction=True,
                human_review_required=False,
            ),
        ]
        return (
            EvidenceLedger(
                topic=dossier.topic,
                claims=claims,
                research_gaps=[],
                extraction_notes=["Deterministic mock artifact; not live research"],
            ),
            self._call("extractor"),
        )

    def write_guide(
        self, brief: ApprovedBrief, ledger: EvidenceLedger
    ) -> tuple[str, AgentCallRecord]:
        guide = """# How Honey Bees Communicate

Honey bees do more than make honey: they also exchange navigational information through movement.
The waggle dance is a striking example of how observable behavior can carry a precise message.

## Reading the dance

A forager can use a **waggle dance** to communicate both the direction and distance of a useful
resource. The angle of the waggle run encodes direction relative to the sun's position.

The important lesson is that the dance is not decorative movement: other bees can use its
features as navigational information.

## How it was decoded

Karl von Frisch's behavioral research helped decode honey bee communication. His experiments
connected features of the dance with the bees' later travel, turning an intriguing behavior into a
testable communication system. He shared the 1973 Nobel Prize in Physiology or Medicine.
"""
        return guide, self._call("guide_author")

    def design(
        self, brief: ApprovedBrief, ledger: EvidenceLedger, guide: str
    ) -> tuple[PackDesign, AgentCallRecord]:
        design = PackDesign(
            pack_id=brief.pack_id,
            pack_name="How Honey Bees Communicate",
            description="A compact introduction to the waggle dance and how scientists decoded it.",
            target_item_count=8,
            target_shape_ratios={
                "fact": 0.25,
                "definition": 0.25,
                "pair": 0.125,
                "mcq": 0.25,
                "numeric": 0.125,
                "procedure": 0.0,
            },
            lessons=[
                LessonPlan(
                    lesson_id="lesson-bee-language",
                    title="Bee communication",
                    rationale="Connect the dance's observable features to the information they carry.",
                    parts=[
                        PartPlan(
                            part_id="part-reading-dance",
                            title="Reading the dance",
                            objective="Interpret the basic information carried by a waggle dance.",
                            guide_heading="Reading the dance",
                            guide_anchor="reading-the-dance",
                            claim_ids=["claim-dance-purpose", "claim-angle"],
                            planned_shapes=["fact", "definition", "pair", "mcq"],
                            visual_opportunities=["Diagram showing angle relative to the sun"],
                        ),
                        PartPlan(
                            part_id="part-decoding",
                            title="How it was decoded",
                            objective="Recognize Karl von Frisch's contribution and its historical context.",
                            guide_heading="How it was decoded",
                            guide_anchor="how-it-was-decoded",
                            claim_ids=["claim-frisch"],
                            planned_shapes=["fact", "definition", "mcq", "numeric"],
                            visual_opportunities=[],
                        ),
                    ],
                )
            ],
            coverage_gaps=[],
            topic_flex_exclusions=[
                "Procedure omitted because this overview does not teach an actionable procedure"
            ],
        )
        return design, self._call("pack_designer")

    def author(
        self,
        brief: ApprovedBrief,
        ledger: EvidenceLedger,
        guide: str,
        design: PackDesign,
    ) -> tuple[AuthoredItems, AgentCallRecord]:
        rows = [
            ItemDraft(
                item_id="fact-waggle-purpose",
                part_id="part-reading-dance",
                claim_ids=["claim-dance-purpose"],
                shape="fact",
                tags=["waggle-dance", "navigation"],
                title="A dance with directions",
                body="A forager's waggle dance communicates both direction and distance to a useful resource.",
            ),
            ItemDraft(
                item_id="def-waggle-dance",
                part_id="part-reading-dance",
                claim_ids=["claim-dance-purpose"],
                shape="definition",
                tags=["waggle-dance"],
                term="Waggle dance",
                definition="A honey bee behavior that communicates navigational information about a resource.",
            ),
            ItemDraft(
                item_id="pair-angle-direction",
                part_id="part-reading-dance",
                claim_ids=["claim-angle"],
                shape="pair",
                tags=["direction", "sun"],
                side_a="Angle of the waggle run",
                side_b="Direction of the resource relative to the sun",
            ),
            ItemDraft(
                item_id="mcq-dance-information",
                part_id="part-reading-dance",
                claim_ids=["claim-dance-purpose"],
                shape="mcq",
                tags=["waggle-dance", "recall"],
                prompt="What information does the waggle dance communicate?",
                options=[
                    "Direction and distance",
                    "Temperature and humidity",
                    "Hive age and size",
                    "Predator color and speed",
                ],
                correct_index=0,
                explanation="The dance encodes navigational information about a useful resource.",
            ),
            ItemDraft(
                item_id="fact-frisch",
                part_id="part-decoding",
                claim_ids=["claim-frisch"],
                shape="fact",
                tags=["history", "scientists"],
                title="Decoding bee communication",
                body="Karl von Frisch's behavioral research helped scientists understand how honey bees communicate.",
            ),
            ItemDraft(
                item_id="def-von-frisch",
                part_id="part-decoding",
                claim_ids=["claim-frisch"],
                shape="definition",
                tags=["history", "scientists"],
                term="Karl von Frisch",
                definition="A zoologist whose research helped decode honey bee communication.",
            ),
            ItemDraft(
                item_id="mcq-frisch-contribution",
                part_id="part-decoding",
                claim_ids=["claim-frisch"],
                shape="mcq",
                tags=["history", "recall"],
                prompt="What was Karl von Frisch known for in bee research?",
                options=[
                    "Decoding bee communication",
                    "Inventing the movable-frame hive",
                    "Discovering royal jelly",
                    "Naming the honey bee",
                ],
                correct_index=0,
                explanation="His behavioral studies helped explain the meaning of bee dances.",
            ),
            ItemDraft(
                item_id="num-frisch-prize",
                part_id="part-decoding",
                claim_ids=["claim-frisch"],
                shape="numeric",
                tags=["history", "numeric"],
                prompt="Year Karl von Frisch shared the Nobel Prize in Physiology or Medicine",
                numeric_value=1973,
                unit="year",
                tolerance=0,
            ),
        ]
        return AuthoredItems(items=rows, author_notes=["Mock authoring artifact"]), self._call(
            "item_author"
        )

    def plan_visuals(
        self,
        ledger: EvidenceLedger,
        design: PackDesign,
        items: AuthoredItems,
    ) -> tuple[VisualPlan, AgentCallRecord]:
        plan = VisualPlan(
            briefs=[
                VisualBrief(
                    asset_id="asset-waggle-angle",
                    item_id="fact-waggle-purpose",
                    teaching_purpose="Show how dance orientation maps to resource direction",
                    kind="diagram",
                    prompt="Draw a clean educational diagram of a honeycomb, a vertical waggle run, the sun, and a food source, with simple arrows and no decorative text.",
                    search_term="honey bee waggle dance diagram",
                    alt_text="Diagram relating a bee's waggle-run angle to the direction of a food source relative to the sun",
                    generate=True,
                )
            ],
            exclusions=["Mock mode does not create an image file"],
        )
        return plan, self._call("visual_director")

    def review(
        self,
        ledger: EvidenceLedger,
        guide: str,
        design: PackDesign,
        items: AuthoredItems,
    ) -> tuple[SemanticReview, AgentCallRecord]:
        review = SemanticReview(
            passed=False,
            findings=[],
            summary="Mock review is structurally complete but cannot authorize publication.",
        )
        return review, self._call("reviewer")

    def generate_image(self, prompt: str) -> bytes:
        raise RuntimeError("Mock mode never fabricates image assets")
