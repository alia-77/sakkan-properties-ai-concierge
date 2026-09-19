import asyncio

from src.mcp_client import call_mcp_tool


def test_mcp_search_listings():
    result = asyncio.run(
        call_mcp_tool(
            "search_listings",
            {
                "district": "New Cairo",
                "max_price": 5_000_000,
                "min_bedrooms": 3,
                "property_type": "apartment",
            },
        )
    )

    assert "results" in result
    assert isinstance(result["results"], list)


def test_mcp_mortgage_calculator():
    result = asyncio.run(
        call_mcp_tool(
            "mortgage_calculator",
            {
                "price": 2_000_000,
                "annual_rate": 18,
                "years": 15,
                "down_payment_percent": 30,
            },
        )
    )

    assert result["property_price"] == 2_000_000
    assert result["monthly_payment"] == 22_546
