import csv
import io

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse, HTMLResponse
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
    query: str = "barbershop"
    target_leads: int = 10


@router.post("/admin/init-db")
def init_db():
    Base.metadata.create_all(bind=engine)

    return {
        "status": "ok",
    }


@router.post("/admin/migrate-lead-intelligence")
def migrate_lead_intelligence(
    db: Session = Depends(get_db),
):
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
        "message": "migration completed",
    }


@router.post("/admin/backfill-intelligence")
def backfill_intelligence(
    limit: int = 100,
    only_missing: bool = True,
    db: Session = Depends(get_db),
):
    query = db.query(Lead)

    if only_missing:
        query = query.filter(Lead.icp_segment.is_(None))

    leads = query.order_by(Lead.created_at.desc()).limit(limit).all()

    updated_count = 0

    for lead in leads:
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

        website_enrichment = enrich_website(
            lead.website,
        )

        intelligence_payload = {
            **lead_data,
            "digital_signals": digital_signals,
            "website_enrichment": website_enrichment,
        }

        analysis = enrich_lead_intelligence(
            intelligence_payload,
        )

        lead.lead_score = (
            analysis.get("lead_score")
            or analysis.get("score")
            or lead.lead_score
        )

        lead.lead_priority = analysis.get("lead_priority")
        lead.digital_maturity = analysis.get("digital_maturity")
        lead.icp_segment = analysis.get("icp_segment")
        lead.main_pain_point = analysis.get("main_pain_point")
        lead.recommended_offer = analysis.get("recommended_offer")
        lead.outreach_angle = analysis.get("outreach_angle")

        row = AIAnalysisResult(
            lead_id=lead.id,
            model="backfill-intelligence",
            result={
                "analysis": analysis,
                "digital_signals": digital_signals,
                "website_enrichment": website_enrichment,
            },
        )

        db.add(row)

        updated_count += 1

    db.commit()

    return {
        "status": "completed",
        "updated_count": updated_count,
    }


@router.get("/dashboard/stats")
def dashboard_stats(
    db: Session = Depends(get_db),
):
    leads = db.query(Lead).all()

    total_leads = len(leads)

    priority_distribution = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "unknown": 0,
    }

    digital_maturity_distribution = {
        "high": 0,
        "medium": 0,
        "low": 0,
        "unknown": 0,
    }

    icp_segments = {}
    cities = {}
    categories = {}

    total_score = 0
    score_count = 0

    for lead in leads:
        priority = lead.lead_priority or "unknown"
        maturity = lead.digital_maturity or "unknown"
        segment = lead.icp_segment or "unknown"
        city = lead.city or "unknown"
        category = lead.category or "unknown"

        priority_distribution[priority] = (
            priority_distribution.get(priority, 0) + 1
        )

        digital_maturity_distribution[maturity] = (
            digital_maturity_distribution.get(maturity, 0) + 1
        )

        icp_segments[segment] = (
            icp_segments.get(segment, 0) + 1
        )

        cities[city] = (
            cities.get(city, 0) + 1
        )

        categories[category] = (
            categories.get(category, 0) + 1
        )

        if lead.lead_score:
            total_score += lead.lead_score
            score_count += 1

    average_lead_score = 0

    if score_count:
        average_lead_score = round(
            total_score / score_count,
            2,
        )

    return {
        "total_leads": total_leads,
        "average_lead_score": average_lead_score,
        "priority_distribution": priority_distribution,
        "digital_maturity_distribution": digital_maturity_distribution,
        "top_icp_segments": dict(
            sorted(
                icp_segments.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:10]
        ),
        "top_cities": dict(
            sorted(
                cities.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:10]
        ),
        "top_categories": dict(
            sorted(
                categories.items(),
                key=lambda item: item[1],
                reverse=True,
            )[:10]
        ),
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(
    db: Session = Depends(get_db),
):
    stats = dashboard_stats(db)

    priority_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in stats["priority_distribution"].items()
    )

    maturity_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in stats["digital_maturity_distribution"].items()
    )

    segment_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in stats["top_icp_segments"].items()
    )

    city_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in stats["top_cities"].items()
    )

    category_rows = "".join(
        f"<tr><td>{k}</td><td>{v}</td></tr>"
        for k, v in stats["top_categories"].items()
    )

    return f"""
    <!doctype html>
    <html>
    <head>
        <title>Lead Intelligence Dashboard</title>

        <style>
            body {{
                font-family: Arial;
                background: #f3f4f6;
                padding: 32px;
                color: #111827;
            }}

            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
                margin-bottom: 24px;
            }}

            .card {{
                background: white;
                padding: 20px;
                border-radius: 14px;
                box-shadow: 0 8px 20px rgba(0,0,0,0.05);
            }}

            .metric {{
                font-size: 34px;
                font-weight: bold;
                margin-top: 8px;
            }}

            .grid {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
                gap: 16px;
            }}

            table {{
                width: 100%;
                border-collapse: collapse;
                margin-top: 12px;
            }}

            td, th {{
                padding: 10px;
                border-bottom: 1px solid #e5e7eb;
                text-align: left;
            }}
        </style>
    </head>

    <body>

        <h1>Lead Intelligence Dashboard</h1>

        <div class="cards">

            <div class="card">
                <div>Total Leads</div>
                <div class="metric">
                    {stats["total_leads"]}
                </div>
            </div>

            <div class="card">
                <div>Average Lead Score</div>
                <div class="metric">
                    {stats["average_lead_score"]}
                </div>
            </div>

        </div>

        <div class="grid">

            <div class="card">
                <h2>Priority Distribution</h2>

                <table>
                    <tr>
                        <th>Priority</th>
                        <th>Count</th>
                    </tr>

                    {priority_rows}
                </table>
            </div>

            <div class="card">
                <h2>Digital Maturity</h2>

                <table>
                    <tr>
                        <th>Level</th>
                        <th>Count</th>
                    </tr>

                    {maturity_rows}
                </table>
            </div>

            <div class="card">
                <h2>Top ICP Segments</h2>

                <table>
                    <tr>
                        <th>Segment</th>
                        <th>Count</th>
                    </tr>

                    {segment_rows}
                </table>
            </div>

            <div class="card">
                <h2>Top Cities</h2>

                <table>
                    <tr>
                        <th>City</th>
                        <th>Count</th>
                    </tr>

                    {city_rows}
                </table>
            </div>

            <div class="card">
                <h2>Top Categories</h2>

                <table>
                    <tr>
                        <th>Category</th>
                        <th>Count</th>
                    </tr>

                    {category_rows}
                </table>
            </div>

        </div>

    </body>
    </html>
    """


@router.post("/campaigns", response_model=CampaignOut)
def create_campaign(
    payload: CampaignCreate,
    db: Session = Depends(get_db),
):
    campaign = Campaign(**payload.model_dump())

    db.add(campaign)
    db.commit()
    db.refresh(campaign)

    return campaign


@router.get("/campaigns", response_model=list[CampaignOut])
def list_campaigns(
    db: Session = Depends(get_db),
):
    return db.query(Campaign).order_by(
        Campaign.created_at.desc(),
    ).all()


@router.post("/leads", response_model=LeadOut)
def create_lead(
    payload: LeadCreate,
    db: Session = Depends(get_db),
):
    data = payload.model_dump()

    data["lead_score"] = score_lead(data)

    lead = Lead(**data)

    db.add(lead)
    db.commit()
    db.refresh(lead)

    return lead


@router.get("/leads", response_model=list[LeadOut])
def list_leads(
    limit: int = 100,
    db: Session = Depends(get_db),
):
    return db.query(Lead).order_by(
        Lead.created_at.desc(),
    ).limit(limit).all()


@router.get("/leads/export")
def export_leads_csv(
    limit: int = 1000,
    db: Session = Depends(get_db),
):
    leads = db.query(Lead).order_by(
        Lead.created_at.desc(),
    ).limit(limit).all()

    output = io.StringIO()

    writer = csv.writer(output)

    writer.writerow([
        "business_name",
        "category",
        "city",
        "rating",
        "lead_score",
        "lead_priority",
        "digital_maturity",
        "icp_segment",
        "main_pain_point",
        "recommended_offer",
    ])

    for lead in leads:
        writer.writerow([
            lead.business_name,
            lead.category,
            lead.city,
            lead.rating,
            lead.lead_score,
            lead.lead_priority,
            lead.digital_maturity,
            lead.icp_segment,
            lead.main_pain_point,
            lead.recommended_offer,
        ])

    output.seek(0)

    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={
            "Content-Disposition":
            "attachment; filename=leads_export.csv",
        },
    )


@router.post("/pipeline/run")
def run_pipeline_sync(
    payload: PipelineRunRequest,
    db: Session = Depends(get_db),
):
    campaign_payload = {
        "name": f"{payload.query} - {payload.city}",
        "country": payload.country,
        "city": payload.city,
        "vertical": payload.query,
        "keywords": [
            payload.query,
            payload.city,
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

    for source_lead in source_leads[:payload.target_leads]:

        lead_payload = {
            "campaign_id": campaign.id,
            "business_name":
                source_lead.get("business_name")
                or "Unknown business",

            "category":
                source_lead.get("category")
                or payload.query,

            "country":
                source_lead.get("country")
                or payload.country,

            "city":
                source_lead.get("city")
                or payload.city,

            "address":
                source_lead.get("address")
                or "",

            "rating":
                source_lead.get("rating")
                or 0.0,

            "reviews_count":
                source_lead.get("reviews_count")
                or 0,

            "phone":
                source_lead.get("phone")
                or "",

            "website":
                source_lead.get("website")
                or "",

            "maps_url":
                source_lead.get("maps_url")
                or "",

            "instagram":
                source_lead.get("instagram")
                or "",

            "telegram":
                source_lead.get("telegram")
                or "",

            "whatsapp":
                source_lead.get("whatsapp")
                or "",

            "source_payload":
                source_lead.get("source_payload")
                or {},
        }

        analysis_payload = {
            "business_name":
                lead_payload["business_name"],

            "category":
                lead_payload["category"],

            "country":
                lead_payload["country"],

            "city":
                lead_payload["city"],

            "rating":
                lead_payload["rating"],

            "reviews_count":
                lead_payload["reviews_count"],

            "website":
                lead_payload["website"],

            "phone":
                lead_payload["phone"],

            "instagram":
                lead_payload["instagram"],

            "telegram":
                lead_payload["telegram"],

            "whatsapp":
                lead_payload["whatsapp"],

            "source_payload":
                lead_payload["source_payload"],
        }

        digital_signals = detect_digital_signals(
            analysis_payload,
        )

        website_enrichment = enrich_website(
            lead_payload["website"],
        )

        intelligence_payload = {
            **analysis_payload,
            "digital_signals":
                digital_signals,

            "website_enrichment":
                website_enrichment,
        }

        analysis = enrich_lead_intelligence(
            intelligence_payload,
        )

        lead_payload["lead_score"] = (
            analysis.get("lead_score")
            or score_lead(lead_payload)
        )

        lead_payload["lead_priority"] = (
            analysis.get("lead_priority")
        )

        lead_payload["digital_maturity"] = (
            analysis.get("digital_maturity")
        )

        lead_payload["icp_segment"] = (
            analysis.get("icp_segment")
        )

        lead_payload["main_pain_point"] = (
            analysis.get("main_pain_point")
        )

        lead_payload["recommended_offer"] = (
            analysis.get("recommended_offer")
        )

        lead_payload["outreach_angle"] = (
            analysis.get("outreach_angle")
        )

        lead = Lead(**lead_payload)

        db.add(lead)
        db.commit()
        db.refresh(lead)

        outreach = generate_ai_outreach({
            **intelligence_payload,
            **analysis,
        })

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

        created_leads.append({
            "lead_id": lead.id,
            "business_name": lead.business_name,
            "lead_score": lead.lead_score,
            "lead_priority": lead.lead_priority,
            "digital_maturity": lead.digital_maturity,
            "icp_segment": lead.icp_segment,
            "analysis": analysis,
            "outreach": outreach,
        })

    return {
        "status": "completed",
        "campaign_id": campaign.id,
        "created_leads_count": len(created_leads),
        "leads": created_leads,
    }
