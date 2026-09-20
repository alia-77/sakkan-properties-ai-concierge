from src.llm import generate_json
from src.observability import event


def detect_language(request_text):
    text = request_text.lower()

    if (
        "arabic" in text
        or "عربي" in text
        or "العربية" in text
    ):
        return "Arabic"

    if "english" in text:
        return "English"

    return "English"


def draft_message(
    trace_id,
    client_name,
    listings,
    mortgage,
    language,
    retrieved=None,
    memory_context=None,
):
    event(
        trace_id,
        "agent_transition",
        agent="comms",
        status="start",
    )

    listings = listings or []
    retrieved = retrieved or []
    memory_context = memory_context or []

    cited_ids = [
        item.get("listing_id")
        for item in listings
        if item.get("listing_id")
    ]

    if not cited_ids:
        cited_ids = [
            item.get("id")
            for item in retrieved
            if item.get("id")
        ]

    prompt = f"""
You are the communication agent for a real-estate concierge.

Draft a client-facing message in {language} for {client_name or "the client"}.

Use only the factual data supplied below. Do not invent listings,
prices, mortgage values, availability, or scheduling details.
Keep the message natural and concise. Match the requested language.
If there are no matching listings, explain that clearly.
If a mortgage calculation is present, summarize its supplied values.

Listings:
{listings}

Mortgage:
{mortgage}

Relevant retrieved documents:
{retrieved}

Relevant client memory:
{memory_context}

Return JSON only:
{{"draft": "message text"}}
"""

    result = generate_json(
        trace_id,
        "comms",
        prompt,
    )

    draft = (
        result.get("draft")
        if result and result.get("draft")
        else None
    )

    if not draft:
        lines = []

        for item in listings:
            lines.append(
                f"{item.get('listing_id')}: "
                f"{item.get('type')} in "
                f"{item.get('district')}, "
                f"{item.get('bedrooms')} bedrooms, "
                f"{item.get('price_egp')} EGP"
            )

        if lines:
            draft = (
                f"Dear {client_name or 'client'}, "
                "here are the shortlisted properties:\n"
                + "\n".join(lines)
            )
        else:
            draft = (
                f"Dear {client_name or 'client'}, "
                "we did not find any matching properties "
                "in the current listings."
            )

        if mortgage and mortgage.get(
            "monthly_payment"
        ):
            draft += (
                f"\n\nEstimated monthly payment: "
                f"{mortgage['monthly_payment']} EGP."
            )

    if cited_ids:
        draft += (
            "\n\nSources: "
            + ", ".join(cited_ids)
        )
    else:
        draft += (
            "\n\nSources: no matching listing "
            "or document IDs"
        )

    event(
        trace_id,
        "draft_created",
        language=language,
        cited_listing_ids=cited_ids,
        llm_generated=bool(result),
    )

    return {
        "draft": draft,
        "language": language,
        "cited_listing_ids": cited_ids,
    }
