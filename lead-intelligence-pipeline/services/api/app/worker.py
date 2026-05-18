from celery import Celery

from app.core.config import settings

celery_app = Celery(
    "lead_intelligence_worker",
    broker=settings.redis_url,
    backend=settings.redis_url,
)


@celery_app.task(name="pipeline.run")
def run_pipeline(campaign_id: str):
    return {
        "status": "completed",
        "campaign_id": campaign_id,
    }
