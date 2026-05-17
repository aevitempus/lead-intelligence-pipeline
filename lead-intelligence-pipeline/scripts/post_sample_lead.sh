#!/usr/bin/env bash
set -euo pipefail
API_URL="${API_URL:-http://localhost:8000}"

curl -s -X POST "$API_URL/api/v1/leads" \
  -H 'Content-Type: application/json' \
  -d '{
    "business_name":"Sample Beauty Studio Bandung",
    "category":"beauty_salon",
    "country":"Indonesia",
    "city":"Bandung",
    "rating":4.6,
    "reviews_count":120,
    "phone":"+62...",
    "website":"https://example.com",
    "instagram":"https://instagram.com/example",
    "whatsapp":"https://wa.me/62...",
    "source_payload":{"source":"manual_sample"}
  }'
