from celery import Celery
from app.core.config import settings

celery_app = Celery(
    "lead_intelligence",
    broker=settings.redis_url,
    backend=settings.redis_url,
)

celery_app.conf.task_routes = {
    "app.workers.tasks.*": {"queue": "default"},
}
