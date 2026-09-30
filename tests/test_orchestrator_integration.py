import asyncio
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.orchestrator import run_concierge


async def approved(draft):
    return "approve", draft


def test_full_listing_communication_flow(monkeypatch):
    from src.agents import triage_agent, comms_agent

    monkeypatch.setattr(
        triage_agent,
        "classify_intent",
        lambda trace_id, text: ["communication"],
    )
    monkeypatch.setattr(
        triage_agent,
        "get_client",
        lambda trace_id, text: ("omar", "Omar"),
    )

    async def fake_mcp(tool_name, arguments):
        assert tool_name == "fetch_listing"
        return {
            "listing_id": arguments["listing_id"],
            "text": "listing_001: real listing",
        }

    monkeypatch.setattr(
        "src.orchestrator.call_mcp_tool",
        fake_mcp,
    )
    monkeypatch.setattr(
        comms_agent,
        "draft_message",
        lambda *args, **kwargs: {
            "draft": "Draft mentioning listing_001.",
            "language": "English",
            "cited_listing_ids": ["listing_001"],
        },
    )

    result = asyncio.run(run_concierge(
        "integration-listing",
        "Draft an English follow-up mentioning listing_001.",
        approve_callback=approved,
    )

    assert result["intents"] == ["communication"]
    assert result["listings"][0]["listing_id"] == "listing_001"
    assert result["hil_decision"] == "approve"
    assert result["final_response"] == "Draft mentioning listing_001."


@pytest.mark.asyncio
def test_full_scheduling_flow_reaches_hil(monkeypatch):
    from src.agents import triage_agent

    monkeypatch.setattr(
        triage_agent,
        "classify_intent",
        lambda trace_id, text: ["scheduling"],
    )
    monkeypatch.setattr(
        triage_agent,
        "get_client",
        lambda trace_id, text: ("hassan", "Hassan"),
    )

    calls = []

    async def fake_mcp(tool_name, arguments):
        calls.append((tool_name, arguments))
        return {
            "status": "scheduled",
            **arguments,
            "reference": "VIEW-0001",
        }

    monkeypatch.setattr(
        "src.orchestrator.call_mcp_tool",
        fake_mcp,
    )

    result = asyncio.run(run_concierge(
        "integration-scheduling",
        "Schedule a viewing for listing_001 for Hassan tomorrow at 15:00.",
        approve_callback=approved,
    )

    assert calls == [
        (
            "schedule_viewing",
            {
                "listing_id": "listing_001",
                "client_id": "hassan",
                "date": "tomorrow",
                "time": "15:00",
            },
        )
    ]
    assert result["intents"] == ["scheduling"]
    assert result["scheduled_viewing"]["status"] == "scheduled"
    assert result["hil_decision"] == "approve"
    assert "VIEW-0001" in result["final_response"]


@pytest.mark.asyncio
def test_full_flow_fails_closed_without_approval(monkeypatch):
    from src.agents import triage_agent

    monkeypatch.setattr(
        triage_agent,
        "classify_intent",
        lambda trace_id, text: ["scheduling"],
    )
    monkeypatch.setattr(
        triage_agent,
        "get_client",
        lambda trace_id, text: ("hassan", "Hassan"),
    )

    async def fake_mcp(tool_name, arguments):
        return {
            "status": "scheduled",
            **arguments,
            "reference": "VIEW-0001",
        }

    monkeypatch.setattr(
        "src.orchestrator.call_mcp_tool",
        fake_mcp,
    )

    result = asyncio.run(run_concierge(
        "integration-no-approval",
        "Schedule a viewing for listing_001 tomorrow at 15:00.",
    )

    assert result["hil_decision"] == "pending"
    assert result["final_response"].startswith(
        "The broker rejected this draft."
    )
