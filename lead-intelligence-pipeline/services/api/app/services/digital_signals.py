from urllib.parse import urlparse


BOOKING_STACKS = {
    "zenoti": "Zenoti",
    "moka": "Moka",
    "booksy": "Booksy",
    "fresha": "Fresha",
    "setmore": "Setmore",
    "calendly": "Calendly",
    "appointy": "Appointy",
    "simplybook": "SimplyBook",
    "chope": "Chope",
    "quandoo": "Quandoo",
    "tablecheck": "TableCheck",
    "opentable": "OpenTable",
    "eatapp": "Eat App",
}


def detect_digital_signals(lead: dict) -> dict:
    website = lead.get("website") or ""
    phone = lead.get("phone") or ""
    instagram = lead.get("instagram") or ""
    whatsapp = lead.get("whatsapp") or ""

    website_lower = website.lower()
    instagram_lower = instagram.lower()
    whatsapp_lower = whatsapp.lower()

    has_website = bool(website)
    has_phone = bool(phone)
    has_instagram = bool(instagram)
    has_whatsapp = bool(whatsapp)

    parsed_domain = ""
    if website:
        try:
            parsed_domain = urlparse(website).netloc.lower()
        except Exception:
            parsed_domain = ""

    has_instagram_as_website = "instagram.com" in website_lower

    detected_booking_stack = None

    for marker, stack_name in BOOKING_STACKS.items():
        if marker in website_lower:
            detected_booking_stack = stack_name
            break

    has_booking_stack = detected_booking_stack is not None

    has_whatsapp_link = (
        "wa.me" in website_lower
        or "whatsapp" in website_lower
        or "wa.me" in whatsapp_lower
        or "whatsapp" in whatsapp_lower
    )

    if has_booking_stack:
        opportunity = "already_digitized"
        opportunity_reason = "Business already uses a booking or reservation platform."
    elif has_instagram_as_website and has_phone:
        opportunity = "instagram_first_business"
        opportunity_reason = "Business relies on Instagram and phone, likely needs structured booking and CRM."
    elif not has_website and has_phone:
        opportunity = "no_website_phone_only"
        opportunity_reason = "Business has phone contact but no website, likely needs digital storefront and booking."
    elif has_website and not has_booking_stack:
        opportunity = "website_without_booking"
        opportunity_reason = "Business has a website but no detected booking or reservation stack."
    else:
        opportunity = "needs_enrichment"
        opportunity_reason = "Insufficient digital footprint data; needs deeper website/social enrichment."

    return {
        "has_website": has_website,
        "website_domain": parsed_domain,
        "has_phone": has_phone,
        "has_instagram": has_instagram,
        "has_whatsapp": has_whatsapp,
        "has_whatsapp_link": has_whatsapp_link,
        "has_instagram_as_website": has_instagram_as_website,
        "has_booking_stack": has_booking_stack,
        "booking_stack": detected_booking_stack,
        "opportunity": opportunity,
        "opportunity_reason": opportunity_reason,
    }
