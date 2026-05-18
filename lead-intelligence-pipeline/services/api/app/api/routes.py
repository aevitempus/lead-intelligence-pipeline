import csv
import io

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.db.session import get_db, Base, engine
from app.models.entities import Campaign, Lead, AIAnalysisResult
from app.schemas.dto import CampaignCreate, CampaignOut, LeadCreate, LeadOut
from app.services.scoring import score_lead
from app.services.lead_sources import search_google_maps_leads
from app.services.digital_signals import detect_digital_signals
from app.services.website_enrichment import enrich_website
from app.services.outreach_generator import generate_outreach

router = APIRouter(prefix="/api/v1")


class PipelineRunRequest(BaseModel):
    country: str = "Indonesia"
    city: str = "Jakarta"
    query: str = "barbershop online booking"
    target_leads: int = 10


def mock_analyze_lead_payload(payload: dict) -> dict:
    business_name = payload.get("business_name", "")
    category = payload.get("category", "")
    city = payload.get("city", "")
    rating = payload.get("rating") or 0
    reviews = payload.get("reviews_count") or 0
    website = payload.get("website") or ""
    phone = payload.get("phone") or ""
    instagram = payload.get("instagram") or ""
    whatsapp = payload.get("whatsapp") or ""

    digital_signals = payload.get("digital_signals") or {}
    website_enrichment = payload.get("website_enrichment") or {}

    score = 40

    if rating >= 4.5:
        score += 20
    elif rating >= 4.0:
        score += 10

    if reviews >= 100:
        score += 20
    elif reviews >= 30:
        score += 10

    if website:
        score += 10

    if phone:
        score += 5

    if instagram:
        score += 5

    if whatsapp:
        score += 5

    if digital_signals.get("has_booking_stack"):
        score -= 10

    if website_enrichment.get("has_online_booking"):
        score -= 10

    if digital_signals.get("opportunity") in [
        "instagram_first_business",
        "no_website_phone_only",
        "website_without_booking",
    ]:
        score += 10

    score = max(0, min(score, 100))

    if score >= 80:
        priority = "high"
    elif score >= 60:
        priority = "medium"
    else:
        priority = "low"

    opportunity = digital_signals.get(
        "opportunity",
        "needs_enrichment",
    )

    opportunity_reason = digital_signals.get(
        "opportunity_reason",
        "Needs deeper enrichment.",
    )

    return {
        "company_summary": (
            f"{business_name} is a {category} SMB in {city}. "
            f"It has a rating of {rating} with {reviews} reviews."
        ),
        "priority": priority,
        "recommended_action": (
            "Offer booking automation, WhatsApp lead capture, "
            "customer reminders, and repeat-visit campaigns."
        ),
        "score": score,
        "opportunity": opportunity,
        "opportunity_reason": opportunity_reason,
        "signals": [
            "SMB business",
            "Potential need for online booking or customer retention automation",
            "Public business profile found",
        ],
    }


@router.post("/admin/init-db")
def init_db():
    Base.metadata.create_all(bind=engine)
    return {"status": "ok"}


@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(payload: CampaignCreate, db: Session = Depends(get_db)):
    campaign = Campaign(**payload.model_dump())
    db.add(campaign)
    db.commit()
    db.refresh(campaign)
    return campaign


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(db: Session = Depends(get_db)):
    return db.query(Campaign).order_by(Campaign.created_at.desc()).all()


@router.post("/leads", response_model=LeadOut)
def create_lead(payload: LeadCreate, db: Session = Depends(get_db)):
    data = payload.model_dump()
    data["lead_score"] = score_lead(data)

    lead = Lead(**data)
    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    status: str | None = None,
    city: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == status)

    if city:
        query = query.filter(Lead.city == city)

    return query.order_by(Lead.created_at.desc()).limit(limit).all()


@router.get("/leads/export")
def export_leads_csv(
    city: str | None = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if city:
        query = query.filter(Lead.city == city)

    leads = query.order_by(Lead.created_at.desc()).limit(limit).all()

    output = io.StringIO()
    writer = csv.writer(output)

    writer.writerow(
        [
            "lead_id",
            "business_name",
            "category",
            "country",
            "city",
            "address",
            "rating",
            "reviews_count",
            "phone",
            "website",
            "maps_url",
            "instagram",
            "telegram",
            "whatsapp",
            "status",
            "lead_score",
            "created_at",
        ]
    )

    for lead in leads:
        writer.writerow(
            [
                lead.id,
                lead.business_name,
                lead.category,
                lead.country,
                lead.city,
                lead.address,
                lead.rating,
                lead.reviews_count,
                lead.phone,
                lead.website,
                lead.maps_url,
                lead.instagram,
                lead.telegram,
                lead.whatsapp,
                lead.status,
                lead.lead_score,
                lead.created_at,
            ]
        )

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition": "attachment; filename=leads_export.csv",
        },
    )


@router.get("/leads/{lead_id}", response_model=LeadOut)
def get_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    return lead


@router.post("/leads/{lead_id}/analyze")
def analyze_lead(lead_id: str, db: Session = Depends(get_db)):
    lead = db.get(Lead, lead_id)

    if not lead:
        raise HTTPException(status_code=404, detail="Lead not found")

    lead_data = {
        "business_name": lead.business_name,
        "category": lead.category,
        "city": lead.city,
        "rating": lead.rating,
        "reviews_count": lead.reviews_count,
        "website": lead.website,
        "phone": lead.phone,
        "instagram": lead.instagram,
        "telegram": lead.telegram,
        "whatsapp": lead.whatsapp,
        "source_payload": lead.source_payload,
    }

    digital_signals = detect_digital_signals(lead_data)

    website_enrichment = enrich_website(
        lead.website,
    )

    lead_data["digital_signals"] = digital_signals
    lead_data["website_enrichment"] = website_enrichment

    result = mock_analyze_lead_payload(lead_data)

    outreach = generate_outreach(
        {
            **lead_data,
            "digital_signals": digital_signals,
            "website_enrichment": website_enrichment,
        }
    )

    row = AIAnalysisResult(
        lead_id=lead.id,
        model="mock-smb",
        result={
            "analysis": result,
            "digital_signals": digital_signals,
            "website_enrichment": website_enrichment,
            "outreach": outreach,
        },
    )

    db.add(row)
    db.commit()

    return {
        "lead_id": lead.id,
        "digital_signals": digital_signals,
        "website_enrichment": website_enrichment,
        "analysis": result,
        "outreach": outreach,
    }


@router.post("/pipeline/run")
def run_pipeline_sync(
    payload: PipelineRunRequest,
    db: Session = Depends(get_db),
):
    campaign_payload = {
        "name": f"{payload.query} - {payload.city}, {payload.country}",
        "country": payload.country,
        "city": payload.city,
        "vertical": payload.query,
        "keywords": [
            payload.query,
            payload.city,
            payload.country,
        ],
        "target_leads": payload.target_leads,
    }

    campaign = Campaign(**campaign_payload)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    source_leads = search_google_maps_leads(
        query=payload.query,
        country=payload.country,
        city=payload.city,
    )

    created_leads = []

    for source_lead in source_leads[: payload.target_leads]:
        lead_payload = {
            "campaign_id": campaign.id,
            "business_name": source_lead.get("business_name") or "Unknown business",
            "category": source_lead.get("category") or payload.query,
            "country": source_lead.get("country") or payload.country,
            "city": source_lead.get("city") or payload.city,
            "address": source_lead.get("address") or "",
            "rating": source_lead.get("rating") or 0.0,
            "reviews_count": source_lead.get("reviews_count") or 0,
            "phone": source_lead.get("phone") or "",
            "website": source_lead.get("website") or "",
            "maps_url": source_lead.get("maps_url") or "",
            "instagram": source_lead.get("instagram") or "",
            "telegram": source_lead.get("telegram") or "",
            "whatsapp": source_lead.get("whatsapp") or "",
            "source_payload": source_lead.get("source_payload") or {},
        }

        lead_payload["lead_score"] = score_lead(
            lead_payload,
        )

        lead = Lead(**lead_payload)
        db.add(lead)
        db.commit()
        db.refresh(lead)

        analysis_payload = {
            "business_name": lead.business_name,
            "category": lead.category,
            "city": lead.city,
            "rating": lead.rating,
            "reviews_count": lead.reviews_count,
            "website": lead.website,
            "phone": lead.phone,
            "instagram": lead.instagram,
            "telegram": lead.telegram,
            "whatsapp": lead.whatsapp,
            "source_payload": lead.source_payload,
        }

        digital_signals = detect_digital_signals(
            analysis_payload,
        )

        website_enrichment = enrich_website(
            lead.website,
        )

        analysis_payload["digital_signals"] = digital_signals
        analysis_payload["website_enrichment"] = website_enrichment

        analysis = mock_analyze_lead_payload(
            analysis_payload,
        )

        outreach = generate_outreach(
            {
                **analysis_payload,
                "digital_signals": digital_signals,
                "website_enrichment": website_enrichment,
            }
        )

        row = AIAnalysisResult(
            lead_id=lead.id,
            model="mock-smb",
            result={
                "analysis": analysis,
                "digital_signals": digital_signals,
                "website_enrichment": website_enrichment,
                "outreach": outreach,
            },
        )

        db.add(row)
        db.commit()

        created_leads.append(
            {
                "lead_id": lead.id,
                "business_name": lead.business_name,
                "category": lead.category,
                "city": lead.city,
                "rating": lead.rating,
                "reviews_count": lead.reviews_count,
                "phone": lead.phone,
                "website": lead.website,
                "maps_url": lead.maps_url,
                "instagram": lead.instagram,
                "whatsapp": lead.whatsapp,
                "lead_score": lead.lead_score,
                "digital_signals": digital_signals,
                "website_enrichment": website_enrichment,
                "analysis": analysis,
                "outreach": outreach,
            }
        )

    return {
        "status": "completed",
        "campaign_id": campaign.id,
        "campaign_name": campaign.name,
        "requested_target_leads": payload.target_leads,
        "created_leads_count": len(created_leads),
        "leads": created_leads,
    }
