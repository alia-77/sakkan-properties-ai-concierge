from src.tools import (
    search_listings,
    fetch_listing,
    mortgage_calculator,
    schedule_viewing,
)


print("SEARCH")
search_result = search_listings(
    {
        "district": "New Cairo",
        "max_price": 5_000_000,
        "min_bedrooms": 3,
        "property_type": "apartment",
    }
)
print(search_result)


print("\nFETCH")
fetch_result = fetch_listing(
    {
        "listing_id": "listing_031",
    }
)
print(fetch_result)


print("\nMORTGAGE")
mortgage_result = mortgage_calculator(
    {
        "price": 5_000_000,
        "annual_rate": 18,
        "years": 15,
        "down_payment_percent": 30,
    }
)
print(mortgage_result)


print("\nSCHEDULE")
schedule_result = schedule_viewing(
    {
        "client_id": "client_01",
        "listing_id": "listing_031",
        "date": "2026-09-01",
        "time": "15:00",
    }
)
print(schedule_result)