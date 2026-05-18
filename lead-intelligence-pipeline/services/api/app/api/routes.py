from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db.session import get_db, Base, engine
from app.models.entities import Campaign, Lead, AIAnalysisResult
from app.schemas.dto import CampaignCreate, CampaignOut, LeadCreate, LeadOut
from app.services.scoring import score_lead
from app.services.ai_gateway import analyze_lead_payload

router = APIRouter(prefix="/api/v1")


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

    result = analyze_lead_payload(payload)

    row = AIAnalysisResult(
        lead_id=lead.id,
        model="configured",
        result=result,
    )

    db.add(row)
    db.commit()

    return {
        "lead_id": lead.id,
        "analysis": result,
    }


@router.post("/pipeline/run")
def run_pipeline_sync(db: Session = Depends(get_db)):
    campaign_payload = {
        "name": "ATM Vendors Indonesia",
        "country": "Indonesia",
        "city": "Jakarta",
        "vertical": "ATM services",
        "keywords": [
            "ATM maintenance",
            "cash management",
            "banking equipment",
        ],
        "target_leads": 10,
    }

    campaign = Campaign(**campaign_payload)
    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    lead_payload = {
        "campaign_id": campaign.id,
        "business_name": "PT ATM Service Indonesia",
        "category": "ATM services",
        "country": "Indonesia",
        "city": "Jakarta",
        "address": "Jakarta",
        "rating": 4.5,
        "reviews_count": 12,
        "phone": "+62 21 123456",
        "website": "https://example.com",
        "maps_url": "https://maps.google.com",
        "instagram": "",
        "telegram": "",
        "whatsapp": "",
        "source_payload": {},
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

    analysis = analyze_lead_payload(analysis_payload)

    row = AIAnalysisResult(
        lead_id=lead.id,
        model="configured",
        result=analysis,
    )

    db.add(row)
    db.commit()

    return {
        "status": "completed",
        "campaign_id": lead.campaign_id,
        "lead_id": lead.id,
        "lead_score": lead.lead_score,
        "analysis": analysis,
    }
