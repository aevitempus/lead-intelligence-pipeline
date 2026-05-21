from pydantic import BaseModel, Field


class CampaignCreate(BaseModel):
    name: str
    country: str = "Indonesia"
    city: str
    vertical: str
    keywords: list[str] = Field(default_factory=list)
    target_leads: int = 100


class CampaignOut(CampaignCreate):
    id: str
    status: str

    class Config:
        from_attributes = True


class LeadCreate(BaseModel):
    campaign_id: str | None = None
    business_name: str
    category: str | None = None
    country: str = "Indonesia"
    city: str
    address: str | None = None
    rating: float | None = None
    reviews_count: int | None = None
    phone: str | None = None
    website: str | None = None
    maps_url: str | None = None
    instagram: str | None = None
    telegram: str | None = None
    whatsapp: str | None = None
    source_payload: dict = Field(default_factory=dict)


class LeadOut(LeadCreate):
    id: str
    status: str

    lead_score: int

    lead_priority: str | None = None
    digital_maturity: str | None = None
    icp_segment: str | None = None

    main_pain_point: str | None = None
    recommended_offer: str | None = None
    outreach_angle: str | None = None

    class Config:
        from_attributes = True
