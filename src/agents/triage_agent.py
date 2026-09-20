import re

from src.llm import generate_json
from src.observability import event


INTENT_KEYWORDS = {
    "property_search": [
        "apartment",
        "villa",
        "townhouse",
        "find",
        "listing",
        "bedroom",
    ],
    "mortgage": [
        "mortgage",
        "loan",
        "down payment",
        "interest",
        "monthly payment",
    ],
    "communication": [
        "message",
        "whatsapp",
        "email",
        "draft",
        "send",
    ],
    "scheduling": [
        "viewing",
        "schedule",
        "visit",
        "appointment",
    ],
}


CLIENTS = {
    "hassan": "hassan",
    "magdy": "magdy",
    "omar": "omar",
    "nour": "nour",
    "mariam": "mariam",
    "youssef": "youssef",
    "salma": "salma",
    "karim": "karim",
}


def extract_client(request_text):
    text = request_text.lower()

    for name, client_id in CLIENTS.items():
        if re.search(
            rf"\b(?:mr\.?|mrs\.?|ms\.?)?\s*{name}\b",
            text,
        ):
            return client_id, name.title()

    return None, None


def classify_intent(trace_id, request_text):
    prompt = f"""
You are the triage agent for a real-estate concierge.

Classify the user's request into zero or more of these intents:
- property_search
- mortgage
- communication
- scheduling

Return JSON only:
{{"intents": ["..."]}}

Rules:
- Include every intent explicitly requested or clearly implied.
- A mortgage request can coexist with property_search.
- A request to draft or send a client message is communication.
- A request for a viewing, visit, appointment, or scheduling is scheduling.
- If none are clear, return property_search.
- Do not invent intents.

User request:
{request_text}
"""

    result = generate_json(
        trace_id,
        "triage",
        prompt,
    )

    intents = result.get("intents", []) if result else []

    allowed = {
        "property_search",
        "mortgage",
        "communication",
        "scheduling",
    }

    intents = [
        intent
        for intent in intents
        if intent in allowed
    ]

    if not intents:
        text = request_text.lower()

        has_mortgage = any(
            keyword in text
            for keyword in [
                "mortgage",
                "loan",
                "down payment",
                "interest",
                "monthly payment",
            ]
        )

        has_property_search = any(
            keyword in text
            for keyword in [
                "apartment",
                "villa",
                "townhouse",
                "find",
                "listing",
                "bedroom",
            ]
        )

        if has_mortgage and not has_property_search:
            intents = ["mortgage"]
        else:
            intents = (
                ["property_search"]
                if not has_property_search
                else ["property_search"]
            )

    event(
        trace_id,
        "agent_transition",
        agent="triage",
        intents=intents,
    )

    return intents


def get_client(trace_id, request_text):
    client_id, client_name = extract_client(
        request_text
    )

    event(
        trace_id,
        "client_identified",
        client_id=client_id,
        client_name=client_name,
    )

    return client_id, client_name
