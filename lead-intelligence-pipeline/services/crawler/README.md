# Local Crawler Node

This service is intended to run on the Lenovo laptop later. For now it contains the contract for pushing discovered leads into the API.

## Flow

1. Collect candidate businesses from approved sources.
2. Normalize lead fields.
3. POST each lead to `/api/v1/leads`.
4. Trigger `/api/v1/leads/{id}/analyze` after enrichment.

## First supported sources

- manual CSV import
- Google/third-party exports
- website enrichment
- later: GrabFood/GoFood collectors
