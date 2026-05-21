import os
from typing import Any

import httpx


def mock_google_maps_leads(query: str, country: str, city: str) -> list[dict[str, Any]]:
    return [
        {
            "business_name": "PT ATM Service Indonesia",
            "category": query,
            "country": country,
            "city": city,
            "address": f"{city}, {country}",
            "rating": 4.5,
            "reviews_count": 12,
            "phone": "+62 21 123456",
            "website": "https://example.com",
            "maps_url": "https://maps.google.com",
            "instagram": "",
            "telegram": "",
            "whatsapp": "",
            "source_payload": {
                "source": "mock",
                "query": query,
            },
        }
    ]


def search_google_maps_leads(query: str, country: str, city: str) -> list[dict[str, Any]]:
    serpapi_key = os.getenv("SERPAPI_KEY")

    if not serpapi_key:
        return mock_google_maps_leads(query=query, country=country, city=city)

    params = {
        "engine": "google_maps",
        "q": f"{query} {city} {country}",
        "api_key": serpapi_key,
    }

    response = httpx.get(
        "https://serpapi.com/search.json",
        params=params,
        timeout=30,
    )
    response.raise_for_status()

    data = response.json()
    local_results = data.get("local_results", [])

    leads = []

    for item in local_results:
        leads.append(
            {
                "business_name": item.get("title") or "Unknown business",
                "category": item.get("type") or query,
                "country": country,
                "city": city,
                "address": item.get("address") or f"{city}, {country}",
                "rating": item.get("rating") or 0.0,
                "reviews_count": item.get("reviews") or 0,
                "phone": item.get("phone") or "",
                "website": item.get("website") or "",
                "maps_url": item.get("link") or "",
                "instagram": "",
                "telegram": "",
                "whatsapp": "",
                "source_payload": item,
            }
        )

    if not leads:
        return mock_google_maps_leads(query=query, country=country, city=city)

    return leads
