# Lead Intelligence Pipeline

MVP pipeline for collecting, enriching, scoring, and preparing SMB leads for AI analysis.

## Stack

- FastAPI
- PostgreSQL
- Redis
- Celery
- Playwright-ready crawler worker
- Docker Compose for local development
- Render-ready Docker deployment

## Local run

```bash
cp .env.example .env
docker compose up --build
```

API: http://localhost:8000
Docs: http://localhost:8000/docs

## First test

```bash
curl http://localhost:8000/health
curl -X POST http://localhost:8000/api/v1/campaigns \
  -H 'Content-Type: application/json' \
  -d '{"name":"Bandung Beauty Pilot","country":"Indonesia","city":"Bandung","vertical":"beauty_salon","keywords":["beauty salon Bandung","skin clinic Bandung"],"target_leads":100}'
```
