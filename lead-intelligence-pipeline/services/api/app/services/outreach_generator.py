from typing import Any


def generate_outreach(lead: dict) -> dict[str, Any]:
    business_name = lead.get("business_name") or "your business"
    category = lead.get("category") or "business"

    digital_signals = lead.get("digital_signals") or {}

    opportunity = digital_signals.get(
        "opportunity",
        "needs_enrichment",
    )

    booking_stack = digital_signals.get(
        "booking_stack",
    )

    if opportunity == "instagram_first_business":
        sales_angle = (
            "Instagram-first businesses often lose leads in DMs "
            "and manual booking processes."
        )

        offer = (
            "WhatsApp booking automation, appointment reminders, "
            "and repeat-customer campaigns."
        )

    elif opportunity == "no_website_phone_only":
        sales_angle = (
            "Businesses without websites often struggle with "
            "manual scheduling and customer retention."
        )

        offer = (
            "Simple online booking page, WhatsApp automation, "
            "and customer reminder system."
        )

    elif opportunity == "website_without_booking":
        sales_angle = (
            "Businesses with websites but without online booking "
            "usually lose conversion opportunities."
        )

        offer = (
            "Integrated booking system, lead capture, "
            "and automated customer follow-ups."
        )

    elif opportunity == "already_digitized":
        sales_angle = (
            "Digitized businesses may still benefit from "
            "retention automation and CRM optimization."
        )

        if booking_stack:
            offer = (
                f"Advanced retention campaigns and CRM integrations "
                f"for businesses already using {booking_stack}."
            )
        else:
            offer = (
                "Retention campaigns and advanced customer analytics."
            )

    else:
        sales_angle = (
            "Potential opportunity for customer engagement automation."
        )

        offer = (
            "Booking automation and repeat-customer workflows."
        )

    cold_email = f"""
Hi {business_name} team,

I noticed that your {category.lower()} business has a strong customer presence online.

{sales_angle}

We help SMB businesses improve booking conversion, automate customer communication, and increase repeat visits.

Potential fit for your business:
- {offer}

Would you be open to a quick conversation?

Best regards
""".strip()

    whatsapp_message = f"""
Hi! I came across {business_name} and noticed potential opportunities to improve booking automation and customer retention for your {category.lower()} business.

Would love to share a few ideas that could help increase repeat customers and reduce manual booking work.
""".strip()

    return {
        "sales_angle": sales_angle,
        "offer": offer,
        "cold_email": cold_email,
        "whatsapp_message": whatsapp_message,
    }
