# Render setup

## Services to create

Use `render.yaml` as a Blueprint or create manually:

1. PostgreSQL instance
2. Redis / Key Value instance
3. Web Service: `lead-intelligence-api`
4. Background Worker: `lead-intelligence-worker`

## Required environment variables

- `DATABASE_URL` - Render Postgres internal connection string. Convert prefix if needed from `postgres://` to SQLAlchemy-compatible `postgresql+psycopg://`.
- `REDIS_URL` - Render Redis internal connection string.
- `OPENAI_API_KEY` - optional at first; without it AI returns stub JSON.
- `AI_MODEL` - default `gpt-4.1-mini`.
- `CRAWLER_API_TOKEN` - random secret for future crawler ingestion.

## Web service

- Runtime: Docker
- Dockerfile path: `./services/api/Dockerfile`
- Health check path: `/health`

## Worker

- Runtime: Docker
- Dockerfile path: `./services/api/Dockerfile`
- Start command: `celery -A app.workers.celery_app worker --loglevel=info`

## First production init

After deploy, open:

`POST https://<your-api>.onrender.com/api/v1/admin/init-db`

Then create first campaign using `/docs`.
