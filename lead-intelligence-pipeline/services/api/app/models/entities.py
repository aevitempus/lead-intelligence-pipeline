import uuid
from datetime import datetime

from sqlalchemy import (
    String,
    Integer,
    Float,
    DateTime,
    ForeignKey,
    JSON,
    Text,
)

from sqlalchemy.orm import (
    Mapped,
    mapped_column,
    relationship,
)

from app.db.session import Base


class Campaign(Base):
    __tablename__ = "campaigns"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    name: Mapped[str] = mapped_column(String(255))
    country: Mapped[str] = mapped_column(String(100))
    city: Mapped[str] = mapped_column(String(100))
    vertical: Mapped[str] = mapped_column(String(100))

    keywords: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    target_leads: Mapped[int] = mapped_column(
        Integer,
        default=100,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="created",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    leads: Mapped[list["Lead"]] = relationship(
        back_populates="campaign",
    )


class Lead(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    campaign_id: Mapped[str | None] = mapped_column(
        String,
        ForeignKey("campaigns.id"),
        nullable=True,
    )

    business_name: Mapped[str] = mapped_column(
        String(255),
    )

    category: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    country: Mapped[str] = mapped_column(
        String(100),
        default="Indonesia",
    )

    city: Mapped[str] = mapped_column(
        String(100),
    )

    address: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    rating: Mapped[float | None] = mapped_column(
        Float,
        nullable=True,
    )

    reviews_count: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
    )

    phone: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    website: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    maps_url: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    instagram: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    telegram: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    whatsapp: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    source_payload: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    status: Mapped[str] = mapped_column(
        String(50),
        default="discovered",
    )

    lead_score: Mapped[int] = mapped_column(
        Integer,
        default=0,
    )

    lead_priority: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    digital_maturity: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
    )

    icp_segment: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    main_pain_point: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recommended_offer: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    outreach_angle: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )

    campaign: Mapped[Campaign] = relationship(
        back_populates="leads",
    )


class LeadSignal(Base):
    __tablename__ = "lead_signals"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    lead_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("leads.id"),
    )

    has_booking: Mapped[bool | None] = mapped_column(
        Integer,
        nullable=True,
    )

    has_chatbot: Mapped[bool | None] = mapped_column(
        Integer,
        nullable=True,
    )

    has_instagram: Mapped[bool | None] = mapped_column(
        Integer,
        nullable=True,
    )

    has_whatsapp: Mapped[bool | None] = mapped_column(
        Integer,
        nullable=True,
    )

    has_telegram: Mapped[bool | None] = mapped_column(
        Integer,
        nullable=True,
    )

    pain_mentions: Mapped[list] = mapped_column(
        JSON,
        default=list,
    )

    raw_signals: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )


class AIAnalysisResult(Base):
    __tablename__ = "ai_analysis_results"

    id: Mapped[str] = mapped_column(
        String,
        primary_key=True,
        default=lambda: str(uuid.uuid4()),
    )

    lead_id: Mapped[str] = mapped_column(
        String,
        ForeignKey("leads.id"),
    )

    model: Mapped[str] = mapped_column(
        String(100),
    )

    result: Mapped[dict] = mapped_column(
        JSON,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.utcnow,
    )
