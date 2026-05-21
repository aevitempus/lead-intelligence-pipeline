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
    failed_count = 0
    results = []

    for lead in leads:
        try:
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

            results.append(
                {
                    "lead_id": lead.id,
                    "business_name": lead.business_name,
                    "lead_score": lead.lead_score,
                    "lead_priority": lead.lead_priority,
                    "digital_maturity": lead.digital_maturity,
                    "icp_segment": lead.icp_segment,
                }
            )

        except Exception as exc:
            failed_count += 1

            results.append(
                {
                    "lead_id": lead.id,
                    "business_name": lead.business_name,
                    "error": str(exc),
                }
            )

    db.commit()

    return {
        "status": "completed",
        "requested_limit": limit,
        "only_missing": only_missing,
        "updated_count": updated_count,
        "failed_count": failed_count,
        "results": results,
    }


@router.get("/dashboard/stats")
def dashboard_stats(db: Session = Depends(get_db)):
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

    score_total = 0
    scored_leads_count = 0

    for lead in leads:
        priority = lead.lead_priority or "unknown"
        maturity = lead.digital_maturity or "unknown"
        segment = lead.icp_segment or "unknown"
        city = lead.city or "unknown"
        category = lead.category or "unknown"

        if priority not in priority_distribution:
            priority_distribution[priority] = 0

        if maturity not in digital_maturity_distribution:
            digital_maturity_distribution[maturity] = 0

        priority_distribution[priority] += 1
        digital_maturity_distribution[maturity] += 1

        icp_segments[segment] = icp_segments.get(segment, 0) + 1
        cities[city] = cities.get(city, 0) + 1
        categories[category] = categories.get(category, 0) + 1

        if lead.lead_score is not None:
            score_total += lead.lead_score
            scored_leads_count += 1

    average_lead_score = None

    if scored_leads_count:
        average_lead_score = round(score_total / scored_leads_count, 2)

    top_icp_segments = dict(
        sorted(
            icp_segments.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]
    )

    top_cities = dict(
        sorted(
            cities.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]
    )

    top_categories = dict(
        sorted(
            categories.items(),
            key=lambda item: item[1],
            reverse=True,
        )[:10]
    )

    return {
        "total_leads": total_leads,
        "average_lead_score": average_lead_score,
        "priority_distribution": priority_distribution,
        "digital_maturity_distribution": digital_maturity_distribution,
        "top_icp_segments": top_icp_segments,
        "top_cities": top_cities,
        "top_categories": top_categories,
    }


@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(db: Session = Depends(get_db)):
    stats = dashboard_stats(db)

    priority_rows = "".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>"
        for key, value in stats["priority_distribution"].items()
    )

    maturity_rows = "".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>"
        for key, value in stats["digital_maturity_distribution"].items()
    )

    segment_rows = "".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>"
        for key, value in stats["top_icp_segments"].items()
    )

    city_rows = "".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>"
        for key, value in stats["top_cities"].items()
    )

    category_rows = "".join(
        f"<tr><td>{key}</td><td>{value}</td></tr>"
        for key, value in stats["top_categories"].items()
    )

    return f"""
    <!doctype html>
    <html>
    <head>
        <title>Lead Intelligence Dashboard</title>

        <style>
            body {{
                font-family: Arial, sans-serif;
                background: #f3f4f6;
                margin: 0;
                padding: 32px;
                color: #111827;
            }}

            h1 {{
                margin-bottom: 4px;
            }}

            .subtitle {{
                color: #6b7280;
                margin-bottom: 28px;
            }}

            .cards {{
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
                gap: 16px;
                margin-bottom: 28px;
            }}

            .card {{
                background: white;
                border-radius: 16px;
                padding: 20px;
                box-shadow: 0 10px 25px rgba(0,0,0,0.06);
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

            th {{
                text-align: left;
                font-size: 13px;
                color: #6b7280;
                border-bottom: 1px solid #e5e7eb;
                padding-bottom: 8px;
            }}

            td {{
                padding: 10px 0;
                border-bottom: 1px solid #f3f4f6;
            }}

            .footer {{
                margin-top: 24px;
                color: #6b7280;
                font-size: 13px;
            }}
        </style>
    </head>

    <body>

        <h1>Lead Intelligence Dashboard</h1>

        <div class="subtitle">
            AI-qualified SMB lead analytics
        </div>

        <div class="cards">

            <div class="card">
                <div>Total Leads</div>
                <div class="metric">{stats["total_leads"]}</div>
            </div>

            <div class="card">
                <div>Average Lead Score</div>
                <div class="metric">{stats["average_lead_score"]}</div>
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
                        <th>Maturity</th>
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

        <div class="footer">
            Data source: PostgreSQL · Endpoint: /api/v1/dashboard/stats
        </div>

    </body>
    </html>
    """
