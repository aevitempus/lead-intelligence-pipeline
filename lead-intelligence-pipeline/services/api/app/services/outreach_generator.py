from typing import Any


def generate_outreach(lead: dict) -> dict[str, Any]:
    business_name = lead.get("business_name") or "your business"
    category = lead.get("category") or "business"

    digital_signals = lead.get("digital_signals") or {}

    opportunity = lead.get("opportunity") or digital_signals.get(
        "opportunity",
        "needs_enrichment",
    )

    booking_stack = digital_signals.get("booking_stack")

    main_pain_point = lead.get("main_pain_point")
    recommended_offer = lead.get("recommended_offer")
    outreach_angle = lead.get("outreach_angle")
    digital_maturity = lead.get("digital_maturity")
    icp_segment = lead.get("icp_segment")

    if main_pain_point and recommended_offer and outreach_angle:
        sales_angle = (
            f"I noticed a potential opportunity around {main_pain_point}. "
            f"The strongest angle is to {outreach_angle}."
        )

        offer = recommended_offer

    elif opportunity == "instagram_first_business":
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
            offer = "Retention campaigns and advanced customer analytics."

    else:
        sales_angle = (
            "Potential opportunity for customer engagement automation."
        )

        offer = "Booking automation and repeat-customer workflows."

    maturity_line = ""
    if digital_maturity:
        maturity_line = f"\nDigital maturity signal: {digital_maturity}."

    segment_line = ""
    if icp_segment:
        segment_line = f"\nICP segment: {icp_segment}."

    cold_email = f"""
Hi {business_name} team,

I came across your {category.lower()} business and noticed a possible opportunity to improve customer booking and follow-up workflows.

{sales_angle}{maturity_line}{segment_line}

We help SMB businesses improve booking conversion, automate customer communication, and increase repeat visits.

Potential fit for your business:
- {offer}

Would you be open to a quick conversation?

Best regards
""".strip()

    whatsapp_message = f"""
Hi! I came across {business_name} and noticed a possible opportunity to improve customer booking and follow-up for your {category.lower()} business.

Main idea: {offer}

Would love to share a few quick ideas that could help reduce manual work and increase repeat customers.
""".strip()

    return {
        "sales_angle": sales_angle,
        "offer": offer,
        "cold_email": cold_email,
        "whatsapp_message": whatsapp_message,
        "main_pain_point": main_pain_point,
        "outreach_angle": outreach_angle,
        "digital_maturity": digital_maturity,
        "icp_segment": icp_segment,
    }
