import re
from typing import Any

import httpx


BOOKING_KEYWORDS = [
    "book now",
    "reservation",
    "reserve",
    "booking",
    "appointment",
    "schedule",
]

BOOKING_PLATFORMS = {
    "zenoti": "Zenoti",
    "fresha": "Fresha",
    "booksy": "Booksy",
    "setmore": "Setmore",
    "calendly": "Calendly",
    "chope": "Chope",
    "quandoo": "Quandoo",
    "opentable": "OpenTable",
}

PAYMENT_KEYWORDS = [
    "stripe",
    "xendit",
    "midtrans",
    "paypal",
]

CHAT_WIDGETS = [
    "tawk.to",
    "intercom",
    "zendesk",
    "livechat",
]


def enrich_website(url: str) -> dict[str, Any]:
    if not url:
        return {
            "website_accessible": False,
        }

    try:
        response = httpx.get(
            url,
            timeout=15,
            follow_redirects=True,
            headers={
                "User-Agent": (
                    "Mozilla/5.0 "
                    "(Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36"
                )
            },
        )

        html = response.text.lower()

    except Exception:
        return {
            "website_accessible": False,
        }

    detected_booking_platforms = []

    for marker, name in BOOKING_PLATFORMS.items():
        if marker in html or marker in url.lower():
            detected_booking_platforms.append(name)

    booking_keywords_found = []

    for keyword in BOOKING_KEYWORDS:
        if keyword in html:
            booking_keywords_found.append(keyword)

    payment_providers = []

    for provider in PAYMENT_KEYWORDS:
        if provider in html:
            payment_providers.append(provider)

    detected_chat_widgets = []

    for widget in CHAT_WIDGETS:
        if widget in html:
            detected_chat_widgets.append(widget)

    whatsapp_links = re.findall(
        r"(wa\.me/[^\s\"']+)",
        html,
    )

    instagram_links = re.findall(
        r"(instagram\.com/[^\s\"']+)",
        html,
    )

    has_online_booking = (
        len(detected_booking_platforms) > 0
        or len(booking_keywords_found) > 0
    )

    return {
        "website_accessible": True,
        "has_online_booking": has_online_booking,
        "booking_keywords_found": booking_keywords_found,
        "booking_platforms": detected_booking_platforms,
        "payment_providers": payment_providers,
        "chat_widgets": detected_chat_widgets,
        "instagram_links_found": instagram_links[:5],
        "whatsapp_links_found": whatsapp_links[:5],
    }
