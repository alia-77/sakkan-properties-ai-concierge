import re

from src.observability import event
from src.settings import MAX_TOOL_CALLS_PER_AGENT
from src.tools import mortgage_calculator


def extract_mortgage_params(request_text, price):
    text = request_text.lower()

    rate_match = re.search(
        r"(\d+(?:\.\d+)?)\s*%",
        text,
    )

    rate = (
        float(rate_match.group(1))
        if rate_match
        else 18.0
    )

    years_match = re.search(
        r"(\d+)\s*(?:year|years)",
        text,
    )

    years = (
        int(years_match.group(1))
        if years_match
        else 15
    )

    down_match = re.search(
        r"(\d+(?:\.\d+)?)\s*%\s*(?:down|down payment)",
        text,
    )

    down_payment = (
        float(down_match.group(1))
        if down_match
        else 30.0
    )

    return {
        "price": price,
        "annual_rate": rate,
        "down_payment_percent": down_payment,
        "years": years,
    }


def run(
    trace_id,
    request_text,
    price,
    tool_call_counter,
):
    event(
        trace_id,
        "agent_transition",
        agent="mortgage_analyst",
        status="start",
    )

    if price is None or price <= 0:
        event(
            trace_id,
            "mortgage_error",
            agent="mortgage_analyst",
            error="no valid property price available",
        )

        return {
            "error": "no valid property price available"
        }

    if (
        tool_call_counter.get(
            "mortgage_analyst",
            0,
        )
        >= MAX_TOOL_CALLS_PER_AGENT
    ):
        event(
            trace_id,
            "tool_call_limit_reached",
            agent="mortgage_analyst",
        )

        return {
            "error": (
                "tool call limit reached, "
                "cannot compute mortgage"
            )
        }

    params = extract_mortgage_params(
        request_text,
        price,
    )

    try:
        result = mortgage_calculator(
            params
        )

        tool_call_counter[
            "mortgage_analyst"
        ] = (
            tool_call_counter.get(
                "mortgage_analyst",
                0,
            )
            + 1
        )

        event(
            trace_id,
            "tool_call",
            agent="mortgage_analyst",
            tool="mortgage_calculator",
            input=params,
            output=result,
        )

        return result

    except Exception as exc:
        event(
            trace_id,
            "tool_error",
            agent="mortgage_analyst",
            tool="mortgage_calculator",
            error=str(exc),
        )

        return {
            "error": "mortgage calculation failed",
            "details": str(exc),
        }