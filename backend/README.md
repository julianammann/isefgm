# giftmanager – Backend

FastAPI-Backend des Geschenke-Managers. Python 3.14, vollständig async, strikt typisiert.

## Stack

| Bereich | Tool |
|---|---|
| Web-Framework | FastAPI |
| ORM | SQLAlchemy 2.0 (async) + asyncpg |
| Migrationen | Alembic (async env) |
| Konfiguration | pydantic-settings (`.env`) |
| Logging | structlog – Console lokal, JSON in Produktion, Request-ID pro Anfrage |
| Packaging | uv, `uv_build`, src-Layout |
| Qualität | Ruff (Lint + Format), Pyright strict |
| Tests | pytest, pytest-asyncio, httpx, testcontainers (echtes Postgres) |

## Struktur

```src/giftmanager/
  __init__.py        __version__ aus pyproject.toml
  main.py            create_app(): CORS, Request-ID-Middleware, Router, Lifespan
  export_openapi.py  Schema-Export für die Frontend-Typen (ohne DB)
  api/v1/            Router und Endpoints (health.py, …)  
  core/
    config.py        Settings – DATABASE_URL, APP_ENV, LOG_LEVEL, CORS_ORIGINS
    db.py            Engine (lazy), Session-Factory, SessionDep
    logging.py       structlog-Konfiguration, Request-ID-Middleware
  models/            SQLAlchemy-Modelle; base.py mit Naming Conventions
  schemas/           Pydantic-Schemas (Request/Response)
  services/          Geschäftslogik, keine HTTP-Abhängigkeit
alembic/             env.py (async), versions/
tests/               conftest.py (Postgres-Container, Savepoint-Rollback pro Test), test_*.py
```

Import-Pfade sind immer absolut: `from giftmanager.core.config import get_settings`.

## KommandosAlle aus `backend/`, alternativ als mise-Task (`mise run <name>`):

| Task | Befehl | Zweck |
|---|---|---|
| `install` | `uv sync` | Dependencies inkl. dev-Gruppe in `.venv` |
| `dev` | `uv run fastapi dev src/giftmanager/main.py` | Server mit Reload, Docs unter `/docs` |
| `lint` | `uv run ruff check . && uv run ruff format --check .` | |
| `fix` | `uv run ruff check --fix . && uv run ruff format .` | Auto-Fix |
| `typecheck` | `uv run pyright` | |
| `test` | `uv run pytest` | braucht Docker |
| `check` | | lint + typecheck + test |
| `migrate` | `uv run alembic upgrade head` | |
| `migration` | `uv run alembic revision --autogenerate -m "…"` | `mise run migration -- "create gifts"` |
| `migrate:check` | `uv run alembic check` | fehlende Migration erkennen |
| `openapi` | `uv run python -m giftmanager.export_openapi > ../frontend/openapi.json` | |

## Konfiguration

`.env` im Repo-Root (Vorlage `.env.example`):

| Variable | Default | Bedeutung |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@localhost:5432/app` | asyncpg-Treiber erforderlich |
| `APP_ENV` | `development` | `development` aktiviert `/docs` und Console-Logs; `production`/`test` → JSON-Logs |
| `LOG_LEVEL` | `INFO` | `DEBUG` zeigt auch SQL, wenn `echo` am Engine aktiv ist |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | JSON-Liste |

## Datenbank und Migrationen

1. Modell in `models/<name>.py` anlegen, von `Base` erben
2. In `models/__init__.py` importieren und in `__all__` aufnehmen – sonst sieht Alembic es nicht
3. `mise run migration -- "create <tabelle>"` (DB muss laufen: `mise run db` im Root)
4. Generierte Datei in `alembic/versions/` gegenlesen – Autogenerate erkennt keine Umbenennungen und keine Datenänderungen
5. `mise run migrate`, dann `mise run migrate:check` → „No new upgrade operations detected"
 
Constraint-Namen folgen der Naming Convention in `models/base.py` (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`) und sind damit in Migrationen deterministisch.

Weitere Befehle: `uv run alembic current`, `history`, `downgrade -1`.

## Tests
```sh
uv run pytest            # alle
uv run pytest -v -k health
```

`conftest.py` startet einmal pro Session ein `postgres:17`-Container, spielt alle Migrationen ein und gibt jedem Test eine Session in einem Savepoint, der danach zurückgerollt wird. Tests prüfen so nebenbei, dass Migrationen und Modelle übereinstimmen. Der erste Lauf lädt das Image (~1 min), danach ~2 s.

## Logging
```python
import structlog
log = structlog.get_logger()
log.info("gift created", gift_id=gift.id)
```

Immer Key-Value statt f-Strings – im JSON-Modus werden daraus filterbare Felder. Die `request_id` aus dem Header `x-request-id` (oder generiert) hängt automatisch an jeder Zeile eines Requests. Uvicorn-, SQLAlchemy- und Alembic-Logs laufen durch denselben Renderer.

## Docker
```sh
docker build --build-arg UV_VERSION=$(mise current uv) -t giftmanager-backend .
```

Multi-Stage: uv-Builder → `python:3.14-slim`, Non-Root-User, nur Produktions-Dependencies. Port 8000. Migrationen laufen nicht im Container-Start, sondern über den `migrate`-Service in `compose.yaml`.

## Endpoints

| Pfad | Zweck |
|---|---|
| `GET /api/v1/health/live` | Prozess läuft |
| `GET /api/v1/health/ready` | DB erreichbar (`database: true`) |
| `GET /docs` | Swagger UI, nur `APP_ENV=development` |
| `GET /openapi.json` | Schema |

