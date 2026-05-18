from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db, Base, engine
from app.models.entities import Campaign, Lead, AIAnalysisResult
from app.schemas.dto import CampaignCreate, CampaignOut, LeadCreate, LeadOut
from app.services.scoring import score_lead
from app.services.lead_sources import search_google_maps_leads

router = APIRouter(prefix="/api/v1")


class PipelineRunRequest(BaseModel):
    country: str = "Indonesia"
    city: str = "Jakarta"
    query: str = "ATM maintenance"
    target_leads: int = 10


def mock_analyze_lead_payload(payload: dict) -> dict:
    return {
        "company_summary": f"{payload.get('business_name')} is a potential lead for {payload.get('category')} in {payload.get('city')}.",
        "priority": "high",
        "recommended_action": "Contact via phone, website, or WhatsApp and offer ATM maintenance services.",
        "score": 87,
        "signals": [
            "Relevant business category",
            "Located in target city",
            "Has public business information",
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

    payload = {
        "business_name": lead.business_name,
        "category": lead.category,
        "city": lead.city,
        "rating": lead.rating,
        "reviews_count": lead.reviews_count,
        "website": lead.website,
        "instagram": lead.instagram,
        "telegram": lead.telegram,
        "whatsapp": lead.whatsapp,
        "source_payload": lead.source_payload,
    }

    result = mock_analyze_lead_payload(payload)

    row = AIAnalysisResult(
        lead_id=lead.id,
        model="mock",
        result=result,
    )

    db.add(row)
    db.commit()

    return {
        "lead_id": lead.id,
        "analysis": result,
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

        lead_payload["lead_score"] = score_lead(lead_payload)

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
            "instagram": lead.instagram,
            "telegram": lead.telegram,
            "whatsapp": lead.whatsapp,
            "source_payload": lead.source_payload,
        }

        analysis = mock_analyze_lead_payload(analysis_payload)

        row = AIAnalysisResult(
            lead_id=lead.id,
            model="mock",
            result=analysis,
        )

        db.add(row)
        db.commit()

        created_leads.append(
            {
                "lead_id": lead.id,
                "business_name": lead.business_name,
                "lead_score": lead.lead_score,
                "analysis": analysis,
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
