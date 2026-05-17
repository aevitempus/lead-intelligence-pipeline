from openai import OpenAI
from app.core.config import settings


def analyze_lead_payload(payload: dict) -> dict:
    """Return structured analysis. If no API key is configured, return a deterministic stub."""
    if not settings.openai_api_key:
        return {
            "business_type": payload.get("category") or "unknown",
            "primary_channel": "whatsapp" if payload.get("whatsapp") else "unknown",
            "automation_need": "unknown",
            "payment_likelihood": "unknown",
            "recommended_outreach_channel": "whatsapp" if payload.get("whatsapp") else "manual_check",
            "recommended_message_angle": "reply instantly to customer inquiries 24/7",
            "confidence": 0.3,
            "reasoning_summary": "OPENAI_API_KEY is not configured; stub analysis returned."
        }

    client = OpenAI(api_key=settings.openai_api_key)
    system = "You analyze Indonesian SMB leads for messaging automation. Return only valid JSON."
    user = {
        "task": "Analyze this lead for WhatsApp/Instagram/Telegram inquiry automation.",
        "lead": payload,
        "required_json_fields": [
            "business_type", "primary_channel", "telegram_relevance", "automation_need",
            "pain_points", "payment_likelihood", "outreach_priority",
            "recommended_outreach_channel", "recommended_message_angle",
            "confidence", "reasoning_summary"
        ]
    }
    response = client.chat.completions.create(
        model=settings.ai_model,
        messages=[
            {"role": "system", "content": system},
            {"role": "user", "content": str(user)},
        ],
        response_format={"type": "json_object"},
        temperature=0.2,
    )
    import json
    return json.loads(response.choices[0].message.content)
