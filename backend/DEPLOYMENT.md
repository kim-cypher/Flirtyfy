# How to run, test, and deploy the production backend

## 1. Prerequisites
- Docker and Docker Compose installed
- OpenAI API key

## 2. Setup
1. Copy `.env.example` to `.env` and fill in secrets (OpenAI key, etc)
2. Run: `docker-compose up --build`
3. In another terminal, run:
   - `docker-compose exec backend python manage.py migrate`
   - `docker-compose exec backend python manage.py createsuperuser`
   - `docker-compose exec backend python manage.py shell < scripts/init_pgvector.sql`

## 3. Usage
- POST `/api/novelty/upload/` with `{ "original_text": "..." }` (auth required)
- GET `/api/novelty/replies/` to list your last 45 days of AI replies

## 4. Testing
- Run: `docker-compose exec backend pytest`

## 5. Scaling
- To add more Celery workers: `docker-compose exec backend celery -A flirty_backend worker --loglevel=info`

## 6. Notes
- All AI generation and novelty checks are async (Celery)
- Redis is used for cache and queue
- pgvector is used for semantic search
- All user data is isolated and secure
- All code is production-grade and maintainable

## 7. Troubleshooting
- Check logs: `docker-compose logs backend`
- Ensure all env vars are set
- Ensure pgvector extension is enabled
- For local dev, you can run Django and Celery separately if needed
