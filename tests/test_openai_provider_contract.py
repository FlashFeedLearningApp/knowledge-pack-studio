from __future__ import annotations

from types import SimpleNamespace

from openai.lib._pydantic import to_strict_json_schema

from knowledge_pack_studio.config import StudioConfig
from knowledge_pack_studio.models import (
    ApprovedBrief,
    AuthoredItems,
    BriefDraft,
    EvidenceLedger,
    PackDesign,
    SemanticReview,
    VisualPlan,
)
from knowledge_pack_studio.provider import MockProvider, OpenAIProvider


class FakeResponses:
    def __init__(self):
        self.request: dict | None = None

    def create(self, **kwargs):
        self.request = kwargs
        return SimpleNamespace(
            id="resp-test",
            output_text="# Research\n\nA grounded result.",
            output=[],
            usage=None,
            model_dump=lambda mode: {
                "output": [
                    {
                        "type": "web_search_call",
                        "action": {
                            "query": "test query",
                            "sources": [
                                {"title": "Primary source", "url": "https://example.org/source"}
                            ],
                        },
                    }
                ]
            },
        )


def test_research_requests_source_details_and_enforces_tool_budget():
    config = StudioConfig(max_web_searches=7)
    draft, _ = MockProvider(config).clarify("Test idea", {})
    brief = ApprovedBrief(
        **draft.model_dump(),
        requester_approved=True,
        approved_at="2026-08-04T00:00:00+00:00",
    )
    fake_responses = FakeResponses()
    fake_client = SimpleNamespace(responses=fake_responses)
    provider = OpenAIProvider(config, {"default": "test-key"})
    provider._client = lambda agent_name: fake_client

    dossier, call = provider.research(brief, [], [])

    assert fake_responses.request is not None
    assert fake_responses.request["tools"] == [{"type": "web_search"}]
    assert fake_responses.request["include"] == ["web_search_call.action.sources"]
    assert fake_responses.request["max_tool_calls"] == 7
    assert dossier.sources[0].url == "https://example.org/source"
    assert call.response_id == "resp-test"


def test_all_structured_output_models_are_strict_schema_compatible():
    """Catch open-ended dictionaries or incomplete required arrays before API calls."""

    def assert_closed_objects(node):
        if isinstance(node, dict):
            if node.get("type") == "object":
                properties = node.get("properties", {})
                assert node.get("additionalProperties") is False
                assert set(node.get("required", [])) == set(properties)
            for value in node.values():
                assert_closed_objects(value)
        elif isinstance(node, list):
            for value in node:
                assert_closed_objects(value)

    for model in (
        BriefDraft,
        EvidenceLedger,
        PackDesign,
        AuthoredItems,
        VisualPlan,
        SemanticReview,
    ):
        assert_closed_objects(to_strict_json_schema(model))
