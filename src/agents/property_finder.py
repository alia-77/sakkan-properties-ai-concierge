import re

from src.rag_chain import retrieve
from src.tools import search_listings
from src.observability import event
from src.settings import MAX_TOOL_CALLS_PER_AGENT


def extract_search_params(request_text):
    text = request_text.lower()

    district = None

    for d in [
        "new cairo",
        "sheikh zayed",
        "6th of october",
        "maadi",
        "north coast",
    ]:
        if d in text:
            district = d.title()
            break

    max_price = None

    price_match = re.search(
        r"(?:under|below|less than)\s+([\d,.]+)\s*(?:m|million)",
        text,
    )

    if price_match:
        max_price = int(
            float(price_match.group(1).replace(",", "")) * 1_000_000
        )

    min_bedrooms = None

    bed_match = re.search(
        r"(\d+)\s*(?:bedrooms?|br)\b",
        text,
    )

    if bed_match:
        min_bedrooms = int(bed_match.group(1))

    property_type = None

    for p in ["apartment", "villa", "townhouse"]:
        if p in text:
            property_type = p
            break

    return {
        "district": district,
        "max_price": max_price,
        "min_bedrooms": min_bedrooms,
        "property_type": property_type,
    }


def run(trace_id, request_text, tool_call_counter):
    event(
        trace_id,
        "agent_transition",
        agent="property_finder",
        status="start",
    )

    try:
        retrieved = retrieve(request_text, top_k=4)
    except Exception as exc:
        event(
            trace_id,
            "rag_error",
            agent="property_finder",
            error=str(exc),
        )
        retrieved = []

    event(
        trace_id,
        "retrieval",
        agent="property_finder",
        doc_ids=[item["id"] for item in retrieved],
    )
    params = extract_search_params(request_text)

    if tool_call_counter.get("property_finder", 0) >= MAX_TOOL_CALLS_PER_AGENT:
        event(
            trace_id,
            "tool_call_limit_reached",
            agent="property_finder",
        )

        return {
            "listings": [],
            "retrieved": retrieved,
            "fallback": True,
        }

    try:
        tool_result = search_listings(params)

        tool_call_counter["property_finder"] = (
            tool_call_counter.get("property_finder", 0) + 1
        )

        event(
            trace_id,
            "tool_call",
            agent="property_finder",
            tool="search_listings",
            input=params,
            output=tool_result,
        )

        listings = tool_result.get("results", [])

        return {
            "listings": listings,
            "retrieved": retrieved,
            "fallback": False,
        }

    except Exception as exc:
        event(
            trace_id,
            "tool_error",
            agent="property_finder",
            tool="search_listings",
            error=str(exc),
        )

        return {
            "listings": [],
            "retrieved": retrieved,
            "fallback": True,
        }
