import re

from src.observability import event


INTENT_KEYWORDS = {
    "property_search": [
        "apartment",
        "villa",
        "townhouse",
        "find",
        "listing",
        "bedroom",
        "property",
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
    text = request_text.lower()

    intents = []

    for intent, keywords in INTENT_KEYWORDS.items():
        if any(
            keyword in text
            for keyword in keywords
        ):
            intents.append(intent)

    if not intents:
        intents = ["property_search"]

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