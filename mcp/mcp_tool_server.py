import sys
from pathlib import Path
from mcp.server.fastmcp import FastMCP

sys.path.append(
    str(Path(__file__).resolve().parents[1])
)

from src.tools import (
    search_listings,
    fetch_listing,
    mortgage_calculator,
    schedule_viewing,
)


mcp_server = FastMCP(
    "sakkan-properties-tools"
)


@mcp_server.tool()
def search_listings_tool(
    district: str | None = None,
    max_price: int | None = None,
    min_bedrooms: int | None = None,
    property_type: str | None = None,
) -> dict:
    return search_listings(
        {
            "district": district,
            "max_price": max_price,
            "min_bedrooms": min_bedrooms,
            "property_type": property_type,
        }
    )


@mcp_server.tool()
def fetch_listing_tool(
    listing_id: str,
) -> dict:
    return fetch_listing(
        {
            "listing_id": listing_id,
        }
    )


@mcp_server.tool()
def mortgage_calculator_tool(
    price: int,
    annual_rate: float,
    years: int,
    down_payment_percent: float,
) -> dict:
    return mortgage_calculator(
        {
            "price": price,
            "annual_rate": annual_rate,
            "years": years,
            "down_payment_percent": down_payment_percent,
        }
    )


@mcp_server.tool()
def schedule_viewing_tool(
    client_id: str,
    listing_id: str,
    date: str,
    time: str,
) -> dict:
    return schedule_viewing(
        {
            "client_id": client_id,
            "listing_id": listing_id,
            "date": date,
            "time": time,
        }
    )


if __name__ == "__main__":
    mcp_server.run()