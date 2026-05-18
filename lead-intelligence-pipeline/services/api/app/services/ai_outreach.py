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

Generate:
1. sales_angle
2. offer
3. cold_email
4. whatsapp_message

Business:
- Name: {business_name}
- Category: {category}
- City: {city}

Digital signals:
{digital_signals}

Website enrichment:
{website_enrichment}

Focus on:
- booking automation
- WhatsApp automation
- retention marketing
- repeat customers
- customer communication
- lead conversion

Keep tone professional and concise.
"""

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        temperature=0.7,
        messages=[
            {
                "role": "system",
                "content": (
                    "You generate highly personalized SMB outbound messaging."
                ),
            },
            {
                "role": "user",
                "content": prompt,
            },
        ],
    )

    content = response.choices[0].message.content

    return {
        "generated_text": content,
    }
