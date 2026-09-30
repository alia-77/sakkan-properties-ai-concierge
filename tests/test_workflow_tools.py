import asyncio
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.orchestrator import listing_action_node, scheduling_node


def test_listing_action_calls_fetch_listing(monkeypatch):
    calls = []

    async def fake_call(tool_name, arguments):
        calls.append((tool_name, arguments))
        return {"listing_id": arguments["listing_id"], "text": "listing"}

    monkeypatch.setattr("src.orchestrator.call_mcp_tool", fake_call)

    result = asyncio.run(
        listing_action_node(
            {
                "request_text": "Draft an English follow-up mentioning listing_001.",
                "client_id": "omar",
                "memory_context": [],
                "retrieved": [],
                "tool_call_counter": {},
                "step_count": 0,
                "trace_id": "test-trace",
            }
        )
    )

    assert calls == [
        ("fetch_listing", {"listing_id": "listing_001"})
    ]
    assert result["listings"][0]["listing_id"] == "listing_001"
    assert result["tool_call_counter"]["listing_action"] == 1


def test_scheduling_calls_schedule_viewing(monkeypatch):
    calls = []

    async def fake_call(tool_name, arguments):
        calls.append((tool_name, arguments))
        return {
            "status": "scheduled",
            **arguments,
            "reference": "VIEW-0001",
        }

    monkeypatch.setattr("src.orchestrator.call_mcp_tool", fake_call)

    result = asyncio.run(
        scheduling_node(
            {
                "request_text": "Schedule a viewing for listing_001 for Hassan tomorrow at 15:00.",
                "client_id": "hassan",
                "tool_call_counter": {},
                "step_count": 0,
                "trace_id": "test-trace",
            }
        )
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
    assert result["scheduled_viewing"]["status"] == "scheduled"
    assert result["tool_call_counter"]["scheduling"] == 1
