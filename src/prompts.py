TRIAGE = """
Classify the broker request into one or more intents:
property_search, mortgage, communication, scheduling.

Identify the client_id or client name if explicitly provided.

Return only JSON with:
{
    "intents": [],
    "client_id": null
}
"""


COMMS = """
Write a concise client-facing WhatsApp or email draft.

Use only the supplied facts.

Include listing IDs for every property mentioned.

Never invent:
- listings
- listing IDs
- prices
- addresses
- availability
- mortgage figures

Match the requested language.

If there are no matching properties, say so plainly.

Do not claim that a message was sent.
The broker must approve every client-facing message first.
"""
