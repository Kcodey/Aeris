# Aeris - Claude Code 项目指南

## Python Environment

This project uses a Conda environment named `aeris`.

Before running Python commands, tests, or development scripts, activate the environment:

```bash
conda activate aeris
```

## Project Structure

```
aeris/
├── main.py                 # FastAPI entry point
├── config.py               # Pydantic settings
├── database.py             # Async SQLAlchemy/SQLModel
├── models/                 # Database models
├── routers/                # API routes (auth, chat, files, tasks)
├── services/               # Business logic (agent, chat, file, task)
├── tools/                  # Agent tools (file, schedule, search)
├── schemas/                # Pydantic schemas
└── utils/                  # Utilities (security, file)
tests/                      # pytest suite
docs/superpowers/plans/     # Implementation plans
```

## Development Commands

Install dependencies:
```bash
pip install -e ".[dev]"
```

Run tests:
```bash
python -m pytest tests/ -v
```

Run specific test file:
```bash
python -m pytest tests/test_task_service.py -v
```

Start development server:
```bash
uvicorn aeris.main:app --reload
```

## Testing Notes

- Tests use SQLite in-memory database (`sqlite+aiosqlite:///:memory:`)
- Fixtures provide per-test database isolation
- `libmagic` is required for file MIME detection (install via `brew install libmagic` on macOS)
