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
):
    event(
        trace_id,
        "agent_transition",
        agent="comms",
        status="start",
    )

    listings = listings or []
    retrieved = retrieved or []

    listing_lines = []

    for item in listings:
        listing_lines.append(
            f"{item.get('listing_id')}: "
            f"{item.get('type')} in "
            f"{item.get('district')}, "
            f"{item.get('bedrooms')} bedrooms, "
            f"{item.get('price_egp')} EGP"
        )

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

    if listing_lines:
        body_en = (
            f"Dear {client_name}, "
            "here are the properties "
            "we shortlisted for you:\n"
            + "\n".join(listing_lines)
        )

        if mortgage and "monthly_payment" in mortgage:
            body_en += (
                f"\n\nEstimated mortgage: "
                f"{mortgage['monthly_payment']} EGP "
                f"per month over "
                f"{mortgage['years']} years at "
                f"{mortgage['rate_pct']}% interest, "
                f"based on a "
                f"{mortgage['property_price']} EGP "
                "property price and "
                f"{mortgage.get('down_payment', 0)} EGP "
                "down payment."
            )

        body_en += (
            "\n\nLet us know if you would like "
            "to schedule a viewing."
        )
    else:
        body_en = (
            f"Dear {client_name}, "
            "we did not find any properties "
            "matching your criteria in our "
            "current listings."
        )

    if language == "Arabic":
        listing_lines_ar = []

        for item in listings:
            listing_lines_ar.append(
                f"{item.get('listing_id')}: "
                f"{item.get('type')} في "
                f"{item.get('district')}, "
                f"{item.get('bedrooms')} غرف نوم, "
                f"{item.get('price_egp')} جنيه"
            )

        if listing_lines_ar:
            body = (
                f"عزيزي {client_name}، "
                "هذه هي العقارات التي اخترناها لك:\n"
                + "\n".join(listing_lines_ar)
            )

            if mortgage and "monthly_payment" in mortgage:
                body += (
                    f"\n\nالتقدير الشهري للقسط: "
                    f"{mortgage['monthly_payment']} جنيه "
                    f"شهرياً على مدى "
                    f"{mortgage['years']} سنة "
                    f"بفائدة "
                    f"{mortgage['rate_pct']}%."
                )

            body += (
                "\n\nأخبرنا إذا كنت ترغب "
                "في تحديد موعد للمعاينة."
            )
        else:
            body = (
                f"عزيزي {client_name}، "
                "لم نجد عقارات مطابقة لمعاييرك "
                "في قوائمنا الحالية."
            )
    else:
        body = body_en

    if cited_ids:
        body += (
            "\n\nSources: "
            + ", ".join(cited_ids)
        )
    else:
        body += (
            "\n\nSources: "
            "no matching listing or document IDs"
        )

    event(
        trace_id,
        "draft_created",
        language=language,
        cited_listing_ids=cited_ids,
    )

    return {
        "draft": body,
        "language": language,
        "cited_listing_ids": cited_ids,
    }