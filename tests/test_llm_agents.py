import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.agents import comms_agent, mortgage_analyst, property_finder, triage_agent


def test_triage_uses_llm_result(monkeypatch):
    monkeypatch.setattr(
        triage_agent,
        "generate_json",
        lambda trace_id, agent, prompt: {
            "intents": ["mortgage", "communication"]
        },
    )

    intents = triage_agent.classify_intent(
        "test-triage",
        "Please prepare a financing message for the client.",
    )

    assert intents == ["mortgage", "communication"]


def test_property_finder_uses_llm_filters(monkeypatch):
    monkeypatch.setattr(
        property_finder,
        "generate_json",
        lambda trace_id, agent, prompt: {
            "district": "New Cairo",
            "max_price": 5000000,
            "min_bedrooms": 3,
            "property_type": "apartment",
        },
    )

    params = property_finder.extract_search_params(
        "test-property",
        "Find suitable homes for this client.",
    )

    assert params == {
        "district": "New Cairo",
        "max_price": 5000000,
        "min_bedrooms": 3,
        "property_type": "apartment",
    }


def test_mortgage_analyst_uses_llm_parameters(monkeypatch):
    monkeypatch.setattr(
        mortgage_analyst,
        "generate_json",
        lambda trace_id, agent, prompt: {
            "annual_rate": 17.5,
            "down_payment_percent": 25,
            "years": 20,
        },
    )

    params = mortgage_analyst.extract_mortgage_params(
        "test-mortgage",
        "Use the client's requested financing terms.",
        4000000,
    )

    assert params == {
        "price": 4000000,
        "annual_rate": 17.5,
        "down_payment_percent": 25.0,
        "years": 20,
    }


def test_comms_agent_uses_llm_draft(monkeypatch):
    monkeypatch.setattr(
        comms_agent,
        "generate_json",
        lambda trace_id, agent, prompt: {
            "draft": "مرحباً حسن، هذه هي الخيارات المناسبة لك."
        },
    )

    result = comms_agent.draft_message(
        trace_id="test-comms",
        client_name="Hassan",
        listings=[
            {
                "listing_id": "listing_001",
                "type": "Apartment",
                "district": "New Cairo",
                "bedrooms": 3,
                "price_egp": 4000000,
            }
        ],
        mortgage=None,
        language="Arabic",
    )

    assert "مرحباً حسن" in result["draft"]
    assert "listing_001" in result["draft"]
