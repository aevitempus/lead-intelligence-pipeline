import csv
import io

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db, Base, engine
from app.models.entities import Campaign, Lead, AIAnalysisResult
from app.schemas.dto import CampaignCreate, CampaignOut, LeadCreate, LeadOut
from app.services.scoring import score_lead
from app.services.lead_sources import search_google_maps_leads
from app.services.digital_signals import detect_digital_signals
from app.services.website_enrichment import enrich_website
from app.services.ai_outreach import generate_ai_outreach
from app.services.lead_intelligence import enrich_lead_intelligence

router = APIRouter(prefix="/api/v1")


class PipelineRunRequest(BaseModel):
    country: str = "Indonesia"
    city: str = "Jakarta"
    query: str = "barbershop online booking"
    target_leads: int = 10


@router.post("/admin/init-db")
def init_db():
    Base.metadata.create_all(bind=engine)
    return {"status": "ok"}


@router.post("/admin/migrate-lead-intelligence")
def migrate_lead_intelligence(db: Session = Depends(get_db)):
    statements = [
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS lead_priority VARCHAR(50)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS digital_maturity VARCHAR(50)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS icp_segment VARCHAR(100)",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS main_pain_point TEXT",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS recommended_offer TEXT",
        "ALTER TABLE leads ADD COLUMN IF NOT EXISTS outreach_angle TEXT",
    ]

    for statement in statements:
        db.execute(text(statement))

    db.commit()

    return {
        "status": "ok",
        "message": "Lead intelligence columns migrated successfully",
    }


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
    icp_segment: str | None = None,
    lead_priority: str | None = None,
    digital_maturity: str | None = None,
    limit: int = 100,
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if status:
        query = query.filter(Lead.status == status)

    if city:
        query = query.filter(Lead.city == city)

    if icp_segment:
        query = query.filter(Lead.icp_segment == icp_segment)

    if lead_priority:
        query = query.filter(Lead.lead_priority == lead_priority)

    if digital_maturity:
        query = query.filter(Lead.digital_maturity == digital_maturity)

    return query.order_by(Lead.created_at.desc()).limit(limit).all()


@router.get("/leads/export")
def export_leads_csv(
    city: str | None = None,
    icp_segment: str | None = None,
    lead_priority: str | None = None,
    digital_maturity: str | None = None,
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if city:
        query = query.filter(Lead.city == city)

    if icp_segment:
        query = query.filter(Lead.icp_segment == icp_segment)

    if lead_priority:
        query = query.filter(Lead.lead_priority == lead_priority)

    if digital_maturity:
        query = query.filter(Lead.digital_maturity == digital_maturity)

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
            "lead_priority",
            "digital_maturity",
            "icp_segment",
            "main_pain_point",
            "recommended_offer",
            "outreach_angle",
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
                lead.lead_priority,
                lead.digital_maturity,
                lead.icp_segment,
                lead.main_pain_point,
                lead.recommended_offer,
                lead.outreach_angle,
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
        "country": lead.country,
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
    website_enrichment = enrich_website(lead.website)

    intelligence_payload = {
        **lead_data,
        "digital_signals": digital_signals,
        "website_enrichment": website_enrichment,
    }

    analysis = enrich_lead_intelligence(intelligence_payload)

    lead.lead_score = analysis.get("lead_score") or analysis.get("score") or lead.lead_score
    lead.lead_priority = analysis.get("lead_priority")
    lead.digital_maturity = analysis.get("digital_maturity")
    lead.icp_segment = analysis.get("icp_segment")
    lead.main_pain_point = analysis.get("main_pain_point")
    lead.recommended_offer = analysis.get("recommended_offer")
    lead.outreach_angle = analysis.get("outreach_angle")

    outreach = generate_ai_outreach(
        {
            **intelligence_payload,
            **analysis,
        }
    )

    row = AIAnalysisResult(
        lead_id=lead.id,
        model="gpt-4o-mini",
        result={
            "analysis": analysis,
            "digital_signals": digital_signals,
            "website_enrichment": website_enrichment,
            "outreach": outreach,
        },
    )

    db.add(row)
    db.commit()
    db.refresh(lead)

    return {
        "lead_id": lead.id,
        "digital_signals": digital_signals,
        "website_enrichment": website_enrichment,
        "analysis": analysis,
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

        analysis_payload = {
            "business_name": lead_payload["business_name"],
            "category": lead_payload["category"],
            "country": lead_payload["country"],
            "city": lead_payload["city"],
            "rating": lead_payload["rating"],
            "reviews_count": lead_payload["reviews_count"],
            "website": lead_payload["website"],
            "phone": lead_payload["phone"],
            "instagram": lead_payload["instagram"],
            "telegram": lead_payload["telegram"],
            "whatsapp": lead_payload["whatsapp"],
            "source_payload": lead_payload["source_payload"],
        }

        digital_signals = detect_digital_signals(analysis_payload)
        website_enrichment = enrich_website(lead_payload["website"])

        intelligence_payload = {
            **analysis_payload,
            "digital_signals": digital_signals,
            "website_enrichment": website_enrichment,
        }

        analysis = enrich_lead_intelligence(intelligence_payload)

        lead_payload["lead_score"] = analysis.get("lead_score") or score_lead(
            lead_payload,
        )
        lead_payload["lead_priority"] = analysis.get("lead_priority")
        lead_payload["digital_maturity"] = analysis.get("digital_maturity")
        lead_payload["icp_segment"] = analysis.get("icp_segment")
        lead_payload["main_pain_point"] = analysis.get("main_pain_point")
        lead_payload["recommended_offer"] = analysis.get("recommended_offer")
        lead_payload["outreach_angle"] = analysis.get("outreach_angle")

        lead = Lead(**lead_payload)
        db.add(lead)
        db.commit()
        db.refresh(lead)

        outreach = generate_ai_outreach(
            {
                **intelligence_payload,
                **analysis,
            }
        )

        row = AIAnalysisResult(
            lead_id=lead.id,
            model="gpt-4o-mini",
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
                "lead_priority": lead.lead_priority,
                "digital_maturity": lead.digital_maturity,
                "icp_segment": lead.icp_segment,
                "main_pain_point": lead.main_pain_point,
                "recommended_offer": lead.recommended_offer,
                "outreach_angle": lead.outreach_angle,
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
