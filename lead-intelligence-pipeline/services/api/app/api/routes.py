from typing import Any


HIGH_VALUE_CATEGORIES = {
    "beauty_salon",
    "barbershop",
    "spa",
    "nail_salon",
    "dental_clinic",
    "clinic",
    "fitness_studio",
    "restaurant",
    "cafe",
}


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value

    if value is None:
        return False

    if isinstance(value, str):
        return value.strip().lower() in {
            "true",
            "yes",
            "1",
            "y",
            "available",
            "found",
        }

    return bool(value)


def normalize_category(category: str | None) -> str:
    if not category:
        return "unknown"

    value = category.strip().lower()

    mapping = {
        "beauty salon": "beauty_salon",
        "salon": "beauty_salon",
        "hair salon": "beauty_salon",
        "barber": "barbershop",
        "barber shop": "barbershop",
        "barbershop": "barbershop",
        "spa": "spa",
        "nail salon": "nail_salon",
        "dental clinic": "dental_clinic",
        "dentist": "dental_clinic",
        "clinic": "clinic",
        "gym": "fitness_studio",
        "fitness": "fitness_studio",
        "fitness studio": "fitness_studio",
        "restaurant": "restaurant",
        "cafe": "cafe",
        "coffee shop": "cafe",
    }

    return mapping.get(value, value.replace(" ", "_"))


def get_nested_bool(data: dict, key: str) -> bool:
    return normalize_bool(data.get(key))


def calculate_intelligence_score(lead: dict) -> int:
    category = normalize_category(lead.get("category"))

    rating = lead.get("rating") or 0
    reviews_count = lead.get("reviews_count") or 0
    website = lead.get("website") or ""
    phone = lead.get("phone") or ""
    instagram = lead.get("instagram") or ""
    whatsapp = lead.get("whatsapp") or ""

    digital_signals = lead.get("digital_signals") or {}
    website_enrichment = lead.get("website_enrichment") or {}

    has_booking_stack = get_nested_bool(digital_signals, "has_booking_stack")
    has_online_booking = get_nested_bool(website_enrichment, "has_online_booking")
    has_website = bool(website)
    has_phone = bool(phone)
    has_instagram = bool(instagram)
    has_whatsapp = bool(whatsapp)

    opportunity = digital_signals.get("opportunity")

    score = 10

    if category in HIGH_VALUE_CATEGORIES:
        score += 12

    if rating >= 4.7:
        score += 12
    elif rating >= 4.3:
        score += 9
    elif rating >= 4.0:
        score += 6

    if reviews_count >= 1000:
        score += 12
    elif reviews_count >= 300:
        score += 10
    elif reviews_count >= 100:
        score += 8
    elif reviews_count >= 30:
        score += 5

    if has_website:
        score += 8

    if has_phone:
        score += 6

    if has_instagram:
        score += 5

    if has_whatsapp:
        score += 8

    if not has_booking_stack:
        score += 8

    if not has_online_booking:
        score += 8

    if opportunity in {
        "instagram_first_business",
        "no_website_phone_only",
        "website_without_booking",
    }:
        score += 8

    if opportunity == "already_digitized":
        score -= 10

    if not has_website and not has_instagram and not has_whatsapp:
        score -= 8

    return max(0, min(score, 100))


def get_lead_priority(score: int) -> str:
    if score >= 80:
        return "high"

    if score >= 55:
        return "medium"

    return "low"


def classify_digital_maturity(lead: dict) -> str:
    website = lead.get("website") or ""
    instagram = lead.get("instagram") or ""
    whatsapp = lead.get("whatsapp") or ""

    digital_signals = lead.get("digital_signals") or {}
    website_enrichment = lead.get("website_enrichment") or {}

    maturity_points = 0

    if website:
        maturity_points += 1

    if instagram:
        maturity_points += 1

    if whatsapp:
        maturity_points += 1

    if digital_signals.get("has_booking_stack"):
        maturity_points += 2

    if website_enrichment.get("has_online_booking"):
        maturity_points += 2

    if website_enrichment.get("has_contact_form"):
        maturity_points += 1

    if maturity_points >= 5:
        return "high"

    if maturity_points >= 3:
        return "medium"

    return "low"


def classify_icp_segment(lead: dict) -> str:
    category = normalize_category(lead.get("category"))

    website = lead.get("website") or ""
    phone = lead.get("phone") or ""
    whatsapp = lead.get("whatsapp") or ""
    instagram = lead.get("instagram") or ""

    digital_signals = lead.get("digital_signals") or {}
    website_enrichment = lead.get("website_enrichment") or {}

    has_booking_stack = get_nested_bool(digital_signals, "has_booking_stack")
    has_online_booking = get_nested_bool(website_enrichment, "has_online_booking")
    has_booking = has_booking_stack or has_online_booking

    if category in {"beauty_salon", "barbershop", "spa", "nail_salon"}:
        if not website and phone and not instagram and not whatsapp:
            return "beauty_phone_only"

        if not website:
            return "beauty_no_website"

        if whatsapp and not has_booking:
            return "beauty_whatsapp_no_booking"

        if website and not has_booking:
            return "beauty_website_no_booking"

        return "beauty_general"

    if category in {"dental_clinic", "clinic"}:
        if not website and phone:
            return "clinic_phone_only"

        if not has_booking:
            return "clinic_no_online_booking"

        return "clinic_general"

    if category in {"restaurant", "cafe"}:
        if not website and phone:
            return "restaurant_phone_only"

        if whatsapp and not has_booking:
            return "restaurant_manual_reservations"

        if not has_booking:
            return "restaurant_no_reservation_system"

        return "restaurant_general"

    if not website and phone:
        return "smb_phone_only"

    if whatsapp and not has_booking:
        return "smb_whatsapp_no_booking"

    if website and not has_booking:
        return "smb_website_no_booking"

    return "general_smb"


def get_main_pain_point(lead: dict) -> str:
    segment = classify_icp_segment(lead)

    if segment == "beauty_phone_only":
        return "customers can only call manually to ask about availability and appointments"

    if segment == "beauty_no_website":
        return "customers cannot easily find a digital booking page or service overview"

    if segment == "beauty_whatsapp_no_booking":
        return "manual WhatsApp booking and missed appointment requests"

    if segment == "beauty_website_no_booking":
        return "website visitors cannot book appointments directly"

    if segment == "clinic_phone_only":
        return "patients need to call manually instead of booking online"

    if segment == "clinic_no_online_booking":
        return "patients cannot book appointments online after working hours"

    if segment == "restaurant_phone_only":
        return "customers need to call manually for reservations or availability"

    if segment == "restaurant_manual_reservations":
        return "manual reservation handling through WhatsApp"

    if segment == "restaurant_no_reservation_system":
        return "no clear online reservation flow"

    if segment == "smb_phone_only":
        return "customer inquiries depend mainly on manual phone calls"

    if segment == "smb_whatsapp_no_booking":
        return "customer inquiries are handled manually through WhatsApp"

    if segment == "smb_website_no_booking":
        return "website visitors cannot easily convert into bookings or inquiries"

    return "limited automation in customer acquisition and booking flow"


def get_recommended_offer(lead: dict) -> str:
    segment = classify_icp_segment(lead)

    if segment in {
        "beauty_phone_only",
        "beauty_no_website",
        "beauty_whatsapp_no_booking",
        "beauty_website_no_booking",
        "beauty_general",
    }:
        return "AI booking assistant for appointments"

    if segment in {
        "clinic_phone_only",
        "clinic_no_online_booking",
        "clinic_general",
    }:
        return "AI receptionist for patient appointment scheduling"

    if segment in {
        "restaurant_phone_only",
        "restaurant_manual_reservations",
        "restaurant_no_reservation_system",
        "restaurant_general",
    }:
        return "AI reservation assistant for restaurants"

    if segment in {
        "smb_phone_only",
        "smb_whatsapp_no_booking",
        "smb_website_no_booking",
    }:
        return "AI assistant for customer inquiries and follow-up"

    return "AI assistant for lead capture and customer follow-up"


def get_outreach_angle(lead: dict) -> str:
    segment = classify_icp_segment(lead)

    if segment == "beauty_phone_only":
        return "turn manual appointment calls into an easier booking flow"

    if segment == "beauty_no_website":
        return "create a simple digital booking flow for new customers"

    if segment == "beauty_whatsapp_no_booking":
        return "reduce missed bookings from WhatsApp messages"

    if segment == "beauty_website_no_booking":
        return "turn website visitors into confirmed appointments"

    if segment == "clinic_phone_only":
        return "reduce manual phone scheduling for patient appointments"

    if segment == "clinic_no_online_booking":
        return "let patients book appointments even outside business hours"

    if segment == "restaurant_phone_only":
        return "make reservations easier without relying only on phone calls"

    if segment == "restaurant_manual_reservations":
        return "automate table reservations and reduce manual replies"

    if segment == "restaurant_no_reservation_system":
        return "make reservations easier for customers"

    if segment == "smb_phone_only":
        return "capture more customer inquiries without relying only on calls"

    if segment == "smb_whatsapp_no_booking":
        return "reply faster to customer inquiries on WhatsApp"

    if segment == "smb_website_no_booking":
        return "convert website traffic into real customer conversations"

    return "increase customer response speed and reduce manual admin work"


def get_recommended_action(lead: dict) -> str:
    offer = get_recommended_offer(lead)
    angle = get_outreach_angle(lead)

    return f"Offer {offer} to {angle}."


def get_recommended_language(lead: dict) -> str:
    country = str(lead.get("country") or "").lower()
    city = str(lead.get("city") or "").lower()

    if "indonesia" in country:
        return "bahasa_indonesia"

    if city in {"jakarta", "bali", "bandung", "surabaya", "medan"}:
        return "bahasa_indonesia"

    return "english"


def enrich_lead_intelligence(lead: dict) -> dict[str, Any]:
    enriched = dict(lead)

    digital_signals = enriched.get("digital_signals") or {}

    score = calculate_intelligence_score(enriched)
    priority = get_lead_priority(score)
    maturity = classify_digital_maturity(enriched)
    icp_segment = classify_icp_segment(enriched)

    main_pain_point = get_main_pain_point(enriched)
    recommended_offer = get_recommended_offer(enriched)
    outreach_angle = get_outreach_angle(enriched)
    recommended_action = get_recommended_action(enriched)

    opportunity = digital_signals.get("opportunity", "needs_enrichment")
    opportunity_reason = digital_signals.get(
        "opportunity_reason",
        "Needs deeper enrichment.",
    )

    enriched.update(
        {
            "score": score,
            "lead_score": score,
            "priority": priority,
            "lead_priority": priority,
            "digital_maturity": maturity,
            "icp_segment": icp_segment,
            "main_pain_point": main_pain_point,
            "recommended_offer": recommended_offer,
            "outreach_angle": outreach_angle,
            "recommended_action": recommended_action,
            "recommended_language": get_recommended_language(enriched),
            "opportunity": opportunity,
            "opportunity_reason": opportunity_reason,
            "company_summary": (
                f"{enriched.get('business_name') or 'This business'} is a "
                f"{enriched.get('category') or 'SMB'} in "
                f"{enriched.get('city') or 'the target city'}."
            ),
            "signals": [
                "SMB business",
                main_pain_point,
                outreach_angle,
            ],
            "intelligence_summary": (
                f"Lead score: {score}/100. "
                f"Priority: {priority}. "
                f"Digital maturity: {maturity}. "
                f"ICP segment: {icp_segment}. "
                f"Pain point: {main_pain_point}. "
                f"Recommended offer: {recommended_offer}."
            ),
        }
    )

    return enriched
