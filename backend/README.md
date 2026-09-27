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
| Code-Referenz | Sphinx (autodoc, napoleon) + sphinx-markdown-builder, Docstrings im Google-Stil |

## Struktur

```src/giftmanager/
  __init__.py        __version__ aus pyproject.toml
  main.py            create_app(): Logging, Request-ID-Middleware, Fehler-Handler, Router
  export_openapi.py  Schema-Export für die Frontend-Typen (ohne DB)
  api/v1/            Router und Endpoints (health.py, auth.py, …)
  core/
    config.py        Settings – DATABASE_URL, APP_ENV, LOG_LEVEL, DEFAULT_TIMEZONE, UPLOADS_DIR
    auth.py          CurrentUser-Dependency, Session-Cookie setzen/löschen
    clock.py         Clock-Protokoll, ClockDep (Zeit injizierbar für Tests und Scheduler)
    db.py            Engine (lazy), Session-Factory, SessionDep (eine Transaktion pro Request)
    errors.py        DomainError, NotFoundError, ConflictError, Problem-Details-Handler
    security.py      Argon2id-Hashing (pwdlib), Session-Token erzeugen und hashen
    logging.py       structlog-Konfiguration, Request-ID-Middleware
  models/            SQLAlchemy-Modelle; base.py mit Naming Conventions und TimestampMixin, user.py als Vorlage. Schema: docs/datenmodell.md
  schemas/           Pydantic-Schemas (Request/Response); common.py mit Page[T] und PageParams
  services/          Geschäftslogik, keine HTTP-Abhängigkeit; auth.py als Vorlage. Erster Parameter ist immer die Session, dann owner_id
alembic/             env.py (async), versions/
tests/               conftest.py (Postgres-Container, Savepoint-Rollback pro Test), test_*.py
```

Import-Pfade sind immer absolut: `from giftmanager.core.config import get_settings`.

## Verbindliche Regeln

**Transaktion.** `get_session` öffnet eine Transaktion pro Request und committet beim Rückgabewert des Endpoints, bei einer Exception wird zurückgerollt. Services rufen nur `await session.flush()`, nie `commit()`.

**Mandantentrennung (Q-01).**
1. Jede kontogebundene Tabelle hat `owner_id` mit `ForeignKey("user_account.id", ondelete="CASCADE")` und Index.
2. Services bekommen `owner_id` als ersten Parameter und filtern jede Query damit. Nie `session.get(Model, id)` ohne Besitzerfilter.
3. Fremde IDs liefern `NotFoundError` (404), nicht 403.
4. Beim Verknüpfen zweier Datensätze prüft der Service, dass beide demselben Konto gehören. Systemweite Anlasstypen (`owner_id IS NULL`) sind ausgenommen.
5. Zu jeder Ressource gehört ein Test „Nutzer B greift auf Ressource von Nutzer A zu → 404“. Ohne diesen Test ist der Endpoint nicht fertig.

**Fehler.** Fachfehler als `DomainError`-Unterklasse aus `core/errors.py` werfen. Kein `HTTPException` in Services.

**Listen.** Jeder Listen-Endpoint nimmt `Annotated[PageParams, Query()]` und liefert `Page[T]` (Q-05).

**Zeit.** `TimestampMixin` für `created_at`. Zeitpunkte `DateTime(timezone=True)`, Kalenderdaten `Date` (Q-08). Aktuelle Zeit nie über `datetime.now()` im Service, sondern über `ClockDep` hereinreichen.

**Dokumentation.** Jede Tabelle und Spalte hat `comment=`, jeder Endpoint `summary` und `description`, jedes Schema-Feld `description` und `examples`, jeder Test `@pytest.mark.requirement("F-xx")`. Diese Texte sind wie der übrige Code Englisch; sie werden zu den MS-4-Dokumenten (`mise run docs`, `docs/dokumentation.md`).

**Docstrings.** Jedes öffentliche Modul, jede Klasse und jede Funktion hat einen Docstring im Google-Stil, Englisch; Ruff (`D1`) prüft das. Klassen-Docstrings in `schemas/` landen zusätzlich in OpenAPI. Daraus erzeugt `mise run apidocs` die Code-Referenz.

**Auth.** Geschützte Router bekommen `dependencies=[Depends(get_current_user)]` oder nehmen `user: CurrentUser` als Parameter. Das Cookie heißt `session`, `HttpOnly`, `SameSite=Lax`, `Secure` außerhalb `development`, Lebensdauer 14 Tage, verlängert bei jeder Nutzung.

## Kommandos

Alle aus `backend/`, alternativ als mise-Task (`mise run <name>`):

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
| `docs` | `uv run python -m giftmanager.export_docs ../docs/generated` | API-, Datenbank- und Konfigurationsdoku aus dem Code (MS 4) |
| `apidocs` | `uv run python docs/build.py ../docs/site/backend` | Code-Referenz als Markdown für die VitePress-Seite; ganze Seite: `mise run apidocs:serve` im Root |

## Konfiguration

`.env` im Repo-Root (Vorlage `.env.example`). Die Tabelle wird aus `core/config.py` erzeugt: `docs/generated/configuration.md`. Kurzfassung:

| Variable | Default | Bedeutung |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@localhost:5432/app` | asyncpg-Treiber erforderlich |
| `APP_ENV` | `production` | `development` aktiviert `/docs`, `/openapi.json` und Console-Logs, Cookie ohne `Secure`; `production`/`test` → JSON-Logs. `mise run dev` und `compose.override.yaml` setzen `development` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DEFAULT_TIMEZONE` | `Europe/Berlin` | Zeitzone für die Auswertung von Kalenderdaten (Scheduler) |
| `UPLOADS_DIR` | `data/uploads` | Ablage für Bild-Uploads, in Produktion ein Volume |
| `SESSION_TTL_DAYS` | `14` | Lebensdauer einer Session |

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

Jeder Test trägt `@pytest.mark.requirement("F-01", "Q-03")` mit den Anforderungs-IDs aus MS 1. Nach jedem Lauf schreibt `conftest.py` die Matrix Anforderung ↔ Test ↔ Ergebnis nach `docs/generated/traceability.md`; ein Teillauf (`-k`) ergibt eine Teilmatrix, deshalb vor dem Commit einmal vollständig laufen lassen.

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
| `POST /api/v1/auth/register` | Konto anlegen, setzt Session-Cookie (201, 409 bei bekannter E-Mail) |
| `POST /api/v1/auth/login` | Anmelden, setzt Session-Cookie (401 bei falschen Daten) |
| `POST /api/v1/auth/logout` | Session widerrufen, Cookie löschen (204, idempotent) |
| `GET /api/v1/auth/me` | Eigenes Konto (401 ohne gültige Session) |
| `DELETE /api/v1/auth/account` | Konto mit allen Daten löschen (204) |
| `GET /docs` | Swagger UI, nur `APP_ENV=development` |
| `GET /openapi.json` | Schema, nur `APP_ENV=development`; Export in jeder Umgebung: `mise run openapi` |
