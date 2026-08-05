from __future__ import annotations

from types import SimpleNamespace

from knowledge_pack_studio.config import StudioConfig
from knowledge_pack_studio.models import ApprovedBrief
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
