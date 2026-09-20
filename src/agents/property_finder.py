import re

from src.llm import generate_json
from src.mcp_client import call_mcp_tool
from src.rag_chain import retrieve
from src.observability import event
from src.settings import MAX_TOOL_CALLS_PER_AGENT


def extract_search_params(trace_id, request_text):
    prompt = f"""
Extract structured property-search filters from the user's request.

Return JSON only with exactly these keys:
{{
  "district": string or null,
  "max_price": integer or null,
  "min_bedrooms": integer or null,
  "property_type": "apartment" | "villa" | "townhouse" | null
}}

Rules:
- Convert prices expressed in millions to EGP.
- "under", "below", or "less than" means max_price.
- Preserve the requested minimum bedroom count.
- Only use districts and property types supported by the request.
- Do not guess missing values.

User request:
{request_text}
"""

    result = generate_json(
        trace_id,
        "property_finder",
        prompt,
    )

    if result:
        return {
            "district": result.get("district"),
            "max_price": result.get("max_price"),
            "min_bedrooms": result.get("min_bedrooms"),
            "property_type": result.get("property_type"),
        }

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
        r"(?:under|below|less than)\s*([\d,.]+)\s*(?:m|million)",
        text,
    )

    if price_match:
        max_price = int(
            float(
                price_match.group(1).replace(",", "")
            )
            * 1_000_000
        )

    min_bedrooms = None

    bed_match = re.search(
        r"(\d+)\s*(?:bedrooms?|br)\b",
        text,
    )

    if bed_match:
        min_bedrooms = int(
            bed_match.group(1)
        )

    property_type = None

    for p in [
        "apartment",
        "villa",
        "townhouse",
    ]:
        if p in text:
            property_type = p
            break

    return {
        "district": district,
        "max_price": max_price,
        "min_bedrooms": min_bedrooms,
        "property_type": property_type,
    }


async def run(trace_id, request_text, tool_call_counter):
    event(
        trace_id,
        "agent_transition",
        agent="property_finder",
        status="start",
    )

    try:
        retrieved = retrieve(
            request_text,
            top_k=4,
        )
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
        doc_ids=[
            item["id"]
            for item in retrieved
        ],
    )

    params = extract_search_params(
        trace_id,
        request_text,
    )

    if tool_call_counter.get(
        "property_finder",
        0,
    ) >= MAX_TOOL_CALLS_PER_AGENT:
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
        tool_result = await call_mcp_tool(
            "search_listings",
            params,
        )

        tool_call_counter["property_finder"] = (
            tool_call_counter.get(
                "property_finder",
                0,
            )
            + 1
        )

        event(
            trace_id,
            "tool_call",
            agent="property_finder",
            tool="search_listings",
            protocol="mcp",
            input=params,
            output=tool_result,
        )

        listings = tool_result.get(
            "results",
            [],
        )

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
            protocol="mcp",
            error=str(exc),
        )

        return {
            "listings": [],
            "retrieved": retrieved,
            "fallback": True,
        }
