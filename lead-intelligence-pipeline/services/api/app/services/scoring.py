def score_lead(lead: dict) -> int:
    score = 0
    if lead.get("whatsapp"):
        score += 20
    if lead.get("instagram"):
        score += 15
    if lead.get("telegram"):
        score += 5
    if lead.get("website"):
        score += 10
    if (lead.get("reviews_count") or 0) >= 50:
        score += 10
    if (lead.get("rating") or 0) >= 4.2:
        score += 10
    return min(score, 100)
