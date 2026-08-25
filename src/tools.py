from pathlib import Path
import math

from pydantic import BaseModel, Field, ValidationError

from src.settings import DATA_DIR


class SearchListingsInput(BaseModel):
    district: str | None = None
    max_price: int | None = None
    min_bedrooms: int | None = None
    property_type: str | None = None
    limit: int = Field(
        default=3,
        ge=1,
        le=10,
    )


class FetchListingInput(BaseModel):
    listing_id: str


class MortgageInput(BaseModel):
    price: int = Field(gt=0)
    annual_rate: float = Field(gt=0, le=100)
    years: int = Field(gt=0, le=40)
    down_payment_percent: float = Field(
        ge=0,
        lt=100,
    )


class ScheduleViewingInput(BaseModel):
    listing_id: str
    client_id: str
    date: str
    time: str


def docs():
    return {
        path.stem: path.read_text(
            encoding="utf-8"
        )
        for path in DATA_DIR.glob("*.txt")
    }


def listing_docs():
    return {
        key: value
        for key, value in docs().items()
        if key.startswith("listing_")
    }


def parse_listing(text):
    data = {}

    for line in text.splitlines():
        if ":" not in line:
            continue

        key, value = line.split(
            ":",
            1,
        )

        key = (
            key.strip()
            .lower()
            .replace(" ", "_")
        )

        data[key] = value.strip()

    return data


def search_listings(args):
    params = SearchListingsInput.model_validate(
        args
    )

    results = []

    for listing_id, text in listing_docs().items():
        listing = parse_listing(text)

        if (
            params.district
            and listing.get("district", "").lower()
            != params.district.lower()
        ):
            continue

        price = int(
            listing.get(
                "price_egp",
                "0",
            ).replace(",", "")
        )

        if (
            params.max_price
            and price > params.max_price
        ):
            continue

        bedrooms = int(
            listing.get(
                "bedrooms",
                "0",
            )
        )

        if (
            params.min_bedrooms
            and bedrooms < params.min_bedrooms
        ):
            continue

        if (
            params.property_type
            and listing.get(
                "type",
                "",
            ).lower()
            != params.property_type.lower()
        ):
            continue

        results.append(
            {
                "listing_id": listing_id,
                **listing,
            }
        )

    return {
        "results": results[: params.limit],
        "count": min(
            len(results),
            params.limit,
        ),
    }


def fetch_listing(args):
    params = FetchListingInput.model_validate(
        args
    )

    text = listing_docs().get(
        params.listing_id
    )

    if not text:
        return {
            "error": "listing_not_found",
            "listing_id": params.listing_id,
        }

    return {
        "listing_id": params.listing_id,
        "text": text,
    }


def mortgage_calculator(args):
    params = MortgageInput.model_validate(args)

    principal = params.price * (
        1 - params.down_payment_percent / 100
    )

    monthly_rate = params.annual_rate / 100 / 12
    number_of_payments = params.years * 12

    payment = (
        principal
        * monthly_rate
        * (1 + monthly_rate) ** number_of_payments
        / (
            (1 + monthly_rate) ** number_of_payments - 1
        )
    )

    return {
        "property_price": params.price,
        "price": params.price,
        "down_payment": round(
            params.price * params.down_payment_percent / 100
        ),
        "loan_amount": round(principal),
        "monthly_payment": round(payment),
        "total_paid": round(
            payment * number_of_payments
        ),
        "total_interest": round(
            payment * number_of_payments - principal
        ),
        "rate_pct": params.annual_rate,
        "years": params.years,
    }


def schedule_viewing(args):
    params = ScheduleViewingInput.model_validate(
        args
    )

    return {
        "status": "scheduled",
        "listing_id": params.listing_id,
        "client_id": params.client_id,
        "date": params.date,
        "time": params.time,
        "reference": (
            "VIEW-"
            + params.listing_id[-4:]
        ),
    }
