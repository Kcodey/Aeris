# Aeris

A lightweight AI Agent platform.

## Development Setup

1. Install dependencies:
```bash
pip install -e ".[dev]"
```

2. Copy environment file:
```bash
cp .env.example .env
```

3. Start PostgreSQL:
```bash
docker-compose up -d db
```

4. Run database migrations:
```bash
alembic upgrade head
```

5. Start development server:
```bash
uvicorn aeris.main:app --reload
```

## Testing

```bash
pytest
```
