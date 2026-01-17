# Project: Online Store Backend (Django + DRF + Strapi + Vue)

## High-level architecture
- Backend: Django + DRF, API-only (no server-rendered frontend)
- CMS: Strapi (external service). Backend fetches products/categories from Strapi.
- Frontend: Vue SPA (separate repo/service). Vue talks ONLY to Django API, not to Strapi directly.
- Email in dev: Mailpit (messages visible at http://localhost:8025)

## How to run (local)
- Use Docker compose:
  - docker compose -f docker-compose.local.yml up --build
- Useful commands:
  - docker compose -f docker-compose.local.yml ps
  - docker compose -f docker-compose.local.yml logs --tail=200 django
  - docker compose -f docker-compose.local.yml run --rm django python manage.py migrate

## Requirements / constraints
- Must support load requirements (target: many concurrent users); prefer caching for /api/products and paginated endpoints.
- Do NOT introduce async stack unless explicitly requested.
- Prefer simple, explainable solutions (this is a thesis project).

## Coding conventions
- DRF: ViewSets/routers where reasonable, serializers clean, validation in serializers.
- Keep endpoints stable: /api/...
- Always add pagination to list endpoints.
- Avoid N+1 queries; use select_related/prefetch_related.
- Use env vars; never commit secrets.

## Domain model (MVP)
- cart: Cart, CartItem(product_id, qty, price_snapshot)
- orders: Order, OrderItem(product_id, qty, price_snapshot, totals)
- products: proxied from Strapi; Django stores minimal references (product_id)

## What to do when implementing changes
1) Propose a short plan (files to touch, commands to run).
2) Make changes incrementally.
3) Run minimal checks (migrations/tests or at least import checks).
4) Summarize what changed and how to run/verify.

## Non-goals
- No integrated frontend pipeline in Django.
- No cloud provider integration unless asked.
