import json
import os

from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
)


def generate_ai_outreach(lead: dict) -> dict:
    business_name = lead.get("business_name", "")
    category = lead.get("category", "")
    city = lead.get("city", "")

    digital_signals = lead.get("digital_signals", {})
    website_enrichment = lead.get("website_enrichment", {})

    prompt = f"""
You are an elite SMB outbound sales strategist.

Generate personalized outreach for this SMB.

Business:
- Name: {business_name}
- Category: {category}
- City: {city}

Digital signals:
{json.dumps(digital_signals, ensure_ascii=False)}

Website enrichment:
{json.dumps(website_enrichment, ensure_ascii=False)}

Focus on:
- booking automation
- WhatsApp automation
- retention marketing
- repeat customers
- customer communication
- lead conversion

Return ONLY valid JSON with this exact schema:
{{
  "sales_angle": "string",
  "offer": "string",
  "cold_email_subject": "string",
  "cold_email": "string",
  "whatsapp_message": "string"
}}

No markdown. No explanations.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.5,
        response_format={
            "type": "json_object",
        },
        messages=[
            {
                "role": "system",
                "content": "You generate concise, personalized SMB outbound messaging as valid JSON.",
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    content = response.choices[0].message.content

    try:
        return json.loads(content)
    except Exception:
        return {
            "sales_angle": "",
            "offer": "",
            "cold_email_subject": "",
            "cold_email": content,
            "whatsapp_message": "",
        }
