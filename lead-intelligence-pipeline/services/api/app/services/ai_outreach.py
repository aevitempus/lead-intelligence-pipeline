from typing import Any


def _clean(value: Any, fallback: str = "") -> str:
    if value is None:
        return fallback

    value = str(value).strip()

    if not value:
        return fallback

    return value


def _get_business_display_name(lead: dict) -> str:
    business_name = _clean(lead.get("business_name"), "your business")

    if " - " in business_name:
        return business_name.split(" - ")[0].strip()

    return business_name


def _get_category_label(lead: dict) -> str:
    category = _clean(lead.get("category"), "business")
    return category.lower()


def _get_location_line(lead: dict) -> str:
    city = _clean(lead.get("city"))
    country = _clean(lead.get("country"))

    if city and country:
        return f"in {city}, {country}"

    if city:
        return f"in {city}"

    if country:
        return f"in {country}"

    return "in your area"


def _build_observation(lead: dict) -> str:
    main_pain_point = _clean(lead.get("main_pain_point"))
    opportunity = _clean(lead.get("opportunity"))
    opportunity_reason = _clean(lead.get("opportunity_reason"))

    website = _clean(lead.get("website"))
    phone = _clean(lead.get("phone"))
    whatsapp = _clean(lead.get("whatsapp"))
    instagram = _clean(lead.get("instagram"))

    if main_pain_point:
        return f"I noticed that {main_pain_point}."

    if opportunity_reason:
        return opportunity_reason

    if opportunity == "no_website_phone_only":
        return (
            "I noticed that customers may currently need to call manually "
            "to ask about availability or appointments."
        )

    if opportunity == "website_without_booking":
        return (
            "I noticed that customers may be able to find the business online, "
            "but may not have a simple way to book directly."
        )

    if opportunity == "instagram_first_business":
        return (
            "I noticed that customer inquiries may be coming through social channels, "
            "which can make bookings harder to track."
        )

    if not website and phone:
        return (
            "I noticed that phone calls may still be the main way customers ask "
            "about availability and appointments."
        )

    if whatsapp and not website:
        return (
            "I noticed that WhatsApp may be the main customer communication channel, "
            "but there may not be a structured booking flow."
        )

    if instagram and not website:
        return (
            "I noticed that Instagram may be an important customer channel, "
            "but there may not be a dedicated booking page."
        )

    return (
        "I noticed a possible opportunity to improve customer booking, "
        "follow-up, and repeat visits."
    )


def _build_offer(lead: dict) -> str:
    recommended_offer = _clean(lead.get("recommended_offer"))
    outreach_angle = _clean(lead.get("outreach_angle"))

    if recommended_offer and outreach_angle:
        return f"{recommended_offer} that helps {outreach_angle}"

    if recommended_offer:
        return recommended_offer

    return "booking automation and customer follow-up workflows"


def _build_sales_angle(lead: dict) -> str:
    observation = _build_observation(lead)
    offer = _build_offer(lead)

    return (
        f"{observation} "
        f"A good next step could be {offer}."
    )


def _build_subject(lead: dict) -> str:
    business_name = _get_business_display_name(lead)
    icp_segment = _clean(lead.get("icp_segment"))

    if icp_segment in {"beauty_phone_only", "beauty_no_website"}:
        return f"Simple booking automation idea for {business_name}"

    if icp_segment in {"beauty_whatsapp_no_booking", "smb_whatsapp_no_booking"}:
        return f"WhatsApp booking idea for {business_name}"

    if icp_segment in {"restaurant_phone_only", "restaurant_manual_reservations"}:
        return f"Reservation automation idea for {business_name}"

    if icp_segment in {"clinic_phone_only", "clinic_no_online_booking"}:
        return f"Appointment automation idea for {business_name}"

    return f"Customer booking automation idea for {business_name}"


def generate_ai_outreach(lead: dict) -> dict[str, Any]:
    business_name = _get_business_display_name(lead)
    category = _get_category_label(lead)
    location_line = _get_location_line(lead)

    lead_score = lead.get("lead_score") or lead.get("score")
    lead_priority = _clean(lead.get("lead_priority") or lead.get("priority"))
    digital_maturity = _clean(lead.get("digital_maturity"))
    icp_segment = _clean(lead.get("icp_segment"))
    main_pain_point = _clean(lead.get("main_pain_point"))
    recommended_offer = _clean(lead.get("recommended_offer"))
    outreach_angle = _clean(lead.get("outreach_angle"))

    sales_angle = _build_sales_angle(lead)
    offer = _build_offer(lead)
    subject = _build_subject(lead)

    context_lines = []

    if lead_score is not None:
        context_lines.append(f"Lead score: {lead_score}/100")

    if lead_priority:
        context_lines.append(f"Priority: {lead_priority}")

    if digital_maturity:
        context_lines.append(f"Digital maturity: {digital_maturity}")

    if icp_segment:
        context_lines.append(f"ICP segment: {icp_segment}")

    context_block = ""
    if context_lines:
        context_block = "\n\nInternal signal summary:\n" + "\n".join(
            f"- {line}" for line in context_lines
        )

    cold_email = f"""
Hi {business_name} team,

I came across {business_name}, a {category} {location_line}.

{_build_observation(lead)}

We help SMBs improve appointment booking, customer communication, and repeat visits with simple automation.

For {business_name}, the most relevant idea would be:
- {offer}

This could help {outreach_angle or "reduce manual admin work and make customer follow-up easier"}.

Would you be open to a quick conversation?

Best regards
""".strip()

    whatsapp_message = f"""
Hi {business_name}! I came across your {category} {location_line}.

{_build_observation(lead)}

Quick idea: {offer}.

Would you be open to seeing a simple way to reduce manual booking work and improve customer follow-up?
""".strip()

    return {
        "sales_angle": sales_angle,
        "offer": offer,
        "cold_email_subject": subject,
        "cold_email": cold_email,
        "whatsapp_message": whatsapp_message,
        "main_pain_point": main_pain_point,
        "recommended_offer": recommended_offer,
        "outreach_angle": outreach_angle,
        "lead_score": lead_score,
        "lead_priority": lead_priority,
        "digital_maturity": digital_maturity,
        "icp_segment": icp_segment,
        "debug_context": context_block.strip(),
    }
