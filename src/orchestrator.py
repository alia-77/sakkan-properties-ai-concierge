import re
from typing import Any, List, Optional, TypedDict

from langgraph.graph import END, StateGraph

from src.agents import (
    comms_agent,
    mortgage_analyst,
    property_finder,
    triage_agent,
)
from src.hil_gate import request_approval
from src.memory import MemoryStore
from src.observability import event
from src.settings import MAX_TOTAL_STEPS


memory_store = MemoryStore()


class ConciergeState(TypedDict, total=False):
    trace_id: str
    request_text: str
    client_id: Optional[str]
    client_name: Optional[str]

    intents: List[str]

    listings: List[dict]
    retrieved: List[dict]

    mortgage: Optional[dict]
    mortgages: List[dict]

    memory_context: List[dict]

    draft: Optional[str]
    language: str
    cited_listing_ids: List[str]

    hil_decision: Optional[str]
    final_response: Optional[str]

    tool_call_counter: dict
    step_count: int

    approve_callback: Any
    fallback: bool


def increment_step(state):
    return state.get("step_count", 0) + 1


def step_limit_reached(state):
    return increment_step(state) > MAX_TOTAL_STEPS


def triage_node(state):
    intents = triage_agent.classify_intent(
        state["trace_id"],
        state["request_text"],
    )

    client_id, client_name = triage_agent.get_client(
        state["trace_id"],
        state["request_text"],
    )

    return {
        "intents": intents,
        "client_id": client_id,
        "client_name": client_name,
        "step_count": increment_step(state),
    }


def memory_read_node(state):
    client_id = state.get("client_id")

    if not client_id:
        return {
            "memory_context": [],
            "step_count": increment_step(state),
        }

    try:
        context = memory_store.search(
            client_id,
            state["request_text"],
        )

        event(
            state["trace_id"],
            "memory_read",
            client_id=client_id,
            hits=len(context),
        )

        return {
            "memory_context": context,
            "step_count": increment_step(state),
        }

    except Exception as exc:
        event(
            state["trace_id"],
            "memory_error",
            client_id=client_id,
            error=str(exc),
        )

        return {
            "memory_context": [],
            "step_count": increment_step(state),
        }


def property_finder_node(state):
    counter = state.get(
        "tool_call_counter",
        {},
    )

    try:
        result = property_finder.run(
            state["trace_id"],
            state["request_text"],
            counter,
        )

        return {
            "listings": result.get(
                "listings",
                [],
            ),
            "retrieved": result.get(
                "retrieved",
                [],
            ),
            "tool_call_counter": counter,
            "fallback": result.get(
                "fallback",
                False,
            ),
            "step_count": increment_step(state),
        }

    except Exception as exc:
        event(
            state["trace_id"],
            "agent_error",
            agent="property_finder",
            error=str(exc),
        )

        return {
            "listings": [],
            "retrieved": [],
            "tool_call_counter": counter,
            "fallback": True,
            "step_count": increment_step(state),
        }


def mortgage_node(state):
    counter = state.get(
        "tool_call_counter",
        {},
    )

    listings = state.get(
        "listings",
        [],
    )

    if not listings:
        price_match = re.search(
            r"(\d+(?:\.\d+)?)\s*(?:m|million)",
            state["request_text"].lower(),
        )

        if price_match:
            price = int(
                float(price_match.group(1)) * 1_000_000
            )

            result = mortgage_analyst.run(
                state["trace_id"],
                state["request_text"],
                price,
                counter,
            )

            return {
                "mortgages": [
                    {
                        "listing_id": None,
                        "calculation": result,
                    }
                ],
                "mortgage": result,
                "tool_call_counter": counter,
                "step_count": increment_step(state),
            }

        return {
            "mortgages": [],
            "mortgage": {
                "error": "no property price available"
            },
            "tool_call_counter": counter,
            "step_count": increment_step(state),
        }

    mortgages = []

    for listing in listings[:3]:
        price = listing.get(
            "price_egp"
        )

        if isinstance(price, str):
            price = int(
                "".join(
                    character
                    for character in price
                    if character.isdigit()
                )
                or 0
            )

        if not price:
            mortgages.append(
                {
                    "listing_id": listing.get(
                        "listing_id"
                    ),
                    "calculation": {
                        "error": (
                            "listing does not contain "
                            "a valid price"
                        )
                    },
                }
            )
            continue

        result = mortgage_analyst.run(
            state["trace_id"],
            state["request_text"],
            price,
            counter,
        )

        mortgages.append(
            {
                "listing_id": listing.get(
                    "listing_id"
                ),
                "calculation": result,
            }
        )

        if (
            counter.get(
                "mortgage_analyst",
                0,
            )
            >= 3
        ):
            break

    return {
        "mortgages": mortgages,
        "mortgage": (
            mortgages[0]["calculation"]
            if mortgages
            else None
        ),
        "tool_call_counter": counter,
        "step_count": increment_step(state),
    }


def comms_node(state):
    language = comms_agent.detect_language(
        state["request_text"]
    )

    result = comms_agent.draft_message(
        state["trace_id"],
        state.get(
            "client_name",
            "client",
        )
        or "client",
        state.get(
            "listings",
            [],
        ),
        state.get(
            "mortgage"
        ),
        language,
        state.get(
            "retrieved",
            [],
        ),
    )

    return {
        "draft": result["draft"],
        "language": result["language"],
        "cited_listing_ids": result[
            "cited_listing_ids"
        ],
        "step_count": increment_step(state),
    }


def property_result_node(state):
    listings = state.get("listings", [])
    retrieved = state.get("retrieved", [])

    if not listings:
        draft = (
            "No matching properties were found "
            "in the current listings.\n\n"
            "Sources: "
            + ", ".join(
                item.get("id", "unknown")
                for item in retrieved
                if item.get("id")
            )
        )
    else:
        lines = []

        for listing in listings:
            lines.append(
                f"{listing.get('listing_id')}: "
                f"{listing.get('type')} in "
                f"{listing.get('district')}, "
                f"{listing.get('bedrooms')} bedrooms, "
                f"{listing.get('price_egp')} EGP"
            )

        source_ids = [
            listing.get("listing_id")
            for listing in listings
            if listing.get("listing_id")
        ]

        draft = (
            "Matching properties:\n"
            + "\n".join(lines)
            + "\n\nSources: "
            + ", ".join(source_ids)
        )

    return {
        "draft": draft,
        "step_count": increment_step(state),
    }


async def hil_node(state):
    draft = state.get(
        "draft"
    )

    if not draft:
        return {
            "hil_decision": "not_required",
            "final_response": state.get(
                "final_response",
                "No client-facing draft was created.",
            ),
            "step_count": increment_step(state),
        }

    result = await request_approval(
        state["trace_id"],
        draft,
        state.get(
            "approve_callback"
        ),
    )

    if result.decision in {
        "approve",
        "edit",
    }:
        final_response = result.final_text

    else:
        final_response = (
            "The broker rejected this draft. "
            "No message was sent to the client."
        )

    return {
        "hil_decision": result.decision,
        "final_response": final_response,
        "step_count": increment_step(state),
    }


def fallback_node(state):
    event(
        state["trace_id"],
        "fallback_triggered",
        step_count=state.get(
            "step_count",
            0,
        ),
    )

    return {
        "final_response": (
            "I could not complete this request confidently "
            "within the allowed processing steps. "
            "Please narrow or rephrase the request."
        ),
        "step_count": increment_step(state),
    }


def route_after_triage(state):
    if step_limit_reached(state):
        return "fallback"

    return "memory_read"


def route_after_memory(state):
    if step_limit_reached(state):
        return "fallback"

    intents = state.get(
        "intents",
        [],
    )

    if "property_search" in intents:
        return "property_finder"

    if "mortgage" in intents:
        return "mortgage_analyst"

    if "communication" in intents:
        return "comms"

    if "scheduling" in intents:
        return "comms"

    return "fallback"


def route_after_property(state):
    if step_limit_reached(state):
        return "fallback"

    if state.get("fallback"):
        return "fallback"

    intents = state.get(
        "intents",
        [],
    )

    if "mortgage" in intents:
        return "mortgage_analyst"

    if "communication" in intents:
        return "comms"

    if "scheduling" in intents:
        return "comms"

    return "property_result"


def route_after_mortgage(state):
    if step_limit_reached(state):
        return "fallback"

    if "communication" in state.get("intents", []):
        return "comms"

    return "mortgage_result"


def route_after_comms(state):
    if step_limit_reached(state):
        return "fallback"

    return "hil"


def mortgage_result_node(state):
    mortgage = state.get("mortgage")

    if not mortgage:
        return {
            "final_response": "Unable to calculate the mortgage."
        }

    return {
        "final_response": (
            f"Mortgage calculation:\n"
            f"Property price: {mortgage['property_price']:,} EGP\n"
            f"Down payment: {mortgage['down_payment']:,} EGP\n"
            f"Loan amount: {mortgage['loan_amount']:,} EGP\n"
            f"Monthly payment: {mortgage['monthly_payment']:,} EGP\n"
            f"Total interest: {mortgage['total_interest']:,} EGP"
        )
    }


def build_graph():
    graph = StateGraph(
        ConciergeState
    )

    graph.add_node(
        "triage",
        triage_node,
    )

    graph.add_node(
        "mortgage_result",
        mortgage_result_node,
    )

    graph.add_node(
        "memory_read",
        memory_read_node,
    )

    graph.add_node(
        "property_finder",
        property_finder_node,
    )

    graph.add_node(
        "mortgage_analyst",
        mortgage_node,
    )

    graph.add_node(
        "comms",
        comms_node,
    )

    graph.add_node(
        "property_result",
        property_result_node,
    )

    graph.add_node(
        "hil",
        hil_node,
    )

    graph.add_node(
        "fallback",
        fallback_node,
    )

    graph.set_entry_point(
        "triage"
    )

    graph.add_conditional_edges(
        "triage",
        route_after_triage,
        {
            "memory_read": "memory_read",
            "fallback": "fallback",
        },
    )

    graph.add_conditional_edges(
        "memory_read",
        route_after_memory,
        {
            "property_finder": "property_finder",
            "mortgage_analyst": "mortgage_analyst",
            "comms": "comms",
            "scheduling": "comms",
            "fallback": "fallback",
        },
    )

    graph.add_conditional_edges(
        "property_finder",
        route_after_property,
        {
            "mortgage_analyst": "mortgage_analyst",
            "comms": "comms",
            "property_result": "property_result",
            "fallback": "fallback",
        },
    )

    graph.add_conditional_edges(
        "mortgage_analyst",
        route_after_mortgage,
        {
            "comms": "comms",
            "mortgage_result": "mortgage_result",
            "property_result": "property_result",
            "fallback": "fallback",
        },
    )

    graph.add_conditional_edges(
        "comms",
        route_after_comms,
        {
            "hil": "hil",
            "fallback": "fallback",
        },
    )

    graph.add_edge(
        "property_result",
        "hil",
    )

    graph.add_edge(
        "hil",
        END,
    )

    graph.add_edge(
        "fallback",
        END,
    )

    graph.add_edge(
        "mortgage_result",
        END,
    )

    return graph.compile()


CONCIERGE_GRAPH = build_graph()


async def run_concierge(
    trace_id,
    request_text,
    client_id=None,
    client_name=None,
    approve_callback=None,
):
    initial_state: ConciergeState = {
        "trace_id": trace_id,
        "request_text": request_text,
        "client_id": client_id,
        "client_name": client_name,
        "tool_call_counter": {},
        "step_count": 0,
        "approve_callback": approve_callback,
        "fallback": False,
    }

    return await CONCIERGE_GRAPH.ainvoke(
        initial_state
    )