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
    ownership.py     owned(), get_owned(), paginate(): Besitzerfilter für kontogebundene Tabellen (Q-01)
alembic/             env.py (async), versions/
tests/               conftest.py (Postgres-Container, Savepoint-Rollback pro Test), test_*.py
  accounts.py        log_in_new_user(): Konto anlegen und auf dem Client anmelden
  ownership.py       assert_invisible_to_other_account(), ITEM_METHODS: Fremdzugriff-Test (Q-01)
```

Import-Pfade sind immer absolut: `from giftmanager.core.config import get_settings`.

## Verbindliche Regeln

**Transaktion.** `get_session` öffnet eine Transaktion pro Request und committet beim Rückgabewert des Endpoints, bei einer Exception wird zurückgerollt. Services rufen nur `await session.flush()`, nie `commit()`.

**Mandantentrennung (Q-01).** Ein Konto sieht und ändert nur seine eigenen Datensätze.
1. Jede kontogebundene Tabelle hat `owner_id` mit `ForeignKey("user_account.id", ondelete="CASCADE")` und Index.
2. Services bekommen nach der Session `owner_id` und lesen kontogebundene Tabellen nur über `services/ownership.py`:
   - `owned(Model, owner_id)` liefert das nach Besitzer gefilterte `SELECT`. Sortierung und weitere Bedingungen hängt der Service an.
   - `get_owned(session, Model, owner_id, id)` liefert den Datensatz oder wirft `NotFoundError`. `update_*` und `delete_*` holen den Datensatz darüber.
   - `paginate(session, stmt, limit=…, offset=…)` liefert Seite und Gesamtzahl aus demselben Statement. So kann die Zählung den Besitzerfilter nicht verlieren.

   Nie `session.get(Model, id)` und kein `select(Model)` ohne `owned()`. Das Modell muss `id` und ein nicht-nullbares `owner_id` haben (Protocol `Owned`), sonst lehnt Pyright den Aufruf ab.
3. Fremde IDs liefern `NotFoundError` (404), nicht 403. Ein 403 würde verraten, dass die ID in einem anderen Konto existiert ([RFC 9110, 15.5.4](https://www.rfc-editor.org/rfc/rfc9110#section-15.5.4), [OWASP API1:2023](https://owasp.org/API-Security/editions/2023/en/0xa1-broken-object-level-authorization/)). `get_owned` unterscheidet „gibt es nicht“ und „gehört jemand anderem“ deshalb nicht.
4. Beim Verknüpfen zweier Datensätze prüft der Service, dass beide demselben Konto gehören. Systemweite Anlasstypen (`owner_id IS NULL`) sind ausgenommen: Sie passen nicht zu `Owned`, `services/occasion.py` filtert sie mit `_visible_types()` und nutzt nur `paginate()`.
5. Zu jeder Ressource gehört ein Test „Nutzer B greift auf Ressource von Nutzer A zu → 404“ mit `assert_invisible_to_other_account` aus `tests/ownership.py`, parametrisiert mit `ITEM_METHODS`. So ist jeder Endpunkt ein eigener Testfall (QZ-06). Der Helfer prüft 404 für die Methode, dass die Liste des fremden Kontos den Datensatz weder zeigt noch mitzählt und dass er danach unverändert ist. `replacement` muss ein gültiger PUT-Body sein, sonst antwortet die Validierung mit 422, bevor der Besitzer geprüft wird. Ohne diesen Test ist der Endpoint nicht fertig.

Neue Ressource, am Beispiel `Person`:

```python
# services/person.py
async def list_people(session: AsyncSession, owner_id: uuid.UUID, *, limit: int, offset: int):
    return await paginate(
        session,
        owned(Person, owner_id).order_by(func.lower(Person.name), Person.id),
        limit=limit,
        offset=offset,
    )


async def get_person(session: AsyncSession, owner_id: uuid.UUID, person_id: uuid.UUID) -> Person:
    return await get_owned(session, Person, owner_id, person_id)


# tests/test_people.py
@pytest.mark.requirement("F-02", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_people_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    lena = (await client.post(PEOPLE, json=LENA)).json()

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=PEOPLE,
        item_id=lena["id"],
        replacement={"name": "Hacked"},
    )
```

Bietet eine Ressource nicht alle Methoden, bekommt `parametrize` eine Teilmenge, etwa `("GET",)`.

**Fehler.** Fachfehler als `DomainError`-Unterklasse aus `core/errors.py` werfen. Kein `HTTPException` in Services.

**Listen.** Jeder Listen-Endpoint nimmt `Annotated[PageParams, Query()]` und liefert `Page[T]` (Q-05).

**Zeit.** `TimestampMixin` für `created_at`. Zeitpunkte `DateTime(timezone=True)`, Kalenderdaten `Date` (Q-08). Aktuelle Zeit nie über `datetime.now()` im Service, sondern über `ClockDep` hereinreichen.

**Dokumentation.** Jede Tabelle und Spalte hat `comment=`, jeder Endpoint `summary` und `description`, jedes Schema-Feld `description` und `examples`, jeder Test `@pytest.mark.requirement("F-xx")`. Diese Texte sind wie der übrige Code Englisch; sie werden zu den MS-4-Dokumenten (`mise run docs`, `docs/dokumentation.md`).

**Docstrings.** Jedes öffentliche Modul, jede Klasse und jede Funktion hat einen Docstring im Google-Stil, Englisch; Ruff (`D1`) prüft das. Klassen-Docstrings in `schemas/` landen zusätzlich in OpenAPI. Daraus erzeugt `mise run apidocs` die Code-Referenz.

**Auth.** Geschützte Router bekommen `dependencies=[Depends(get_current_user)]` oder nehmen `user: CurrentUser` als Parameter. Das Cookie heißt `__Host-session`, `HttpOnly`, `SameSite=Lax`, `Secure`, `Path=/`, ohne `Domain`. Ein `__Host-`-Cookie nimmt der Browser nur mit `Secure`, `Path=/` und ohne `Domain` an, deshalb kann eine Nachbar-Subdomain es weder setzen noch überdecken (Cookie Tossing); ein untergeschobenes `session` liest das Backend nicht. In `development` heißt es `session` und ist nicht `Secure`, weil Browser ein `__Host-`-Cookie ohne `Secure` über http ablehnen. Die Namen stehen in `core/auth.py` und müssen zu `SESSION_COOKIES` in `frontend/src/lib/server/session.ts` passen. Lebensdauer 14 Tage, verlängert bei jeder Nutzung, aber nie über 30 Tage ab der Anmeldung hinaus. Danach ist eine neue Anmeldung nötig. Jede Anmeldung löscht die abgelaufenen Sessions des Kontos.

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
| `create-user` | `uv run python -m giftmanager.create_user` | Konto anlegen, auch bei geschlossener Registrierung; fragt das Passwort ab. `mise run create-user -- --email anna@example.org --display-name Anna`, auf dem Server `docker compose exec api python -m giftmanager.create_user …` |
| `openapi` | `uv run python -m giftmanager.export_openapi > ../frontend/openapi.json` | |
| `docs` | `uv run python -m giftmanager.export_docs ../docs/generated` | API-, Datenbank- und Konfigurationsdoku aus dem Code (MS 4) |
| `apidocs` | `uv run python docs/build.py ../docs/site/backend` | Code-Referenz als Markdown für die VitePress-Seite; ganze Seite: `mise run apidocs:serve` im Root |

## Konfiguration

`.env` im Repo-Root (Vorlage `.env.example`). Die Tabelle wird aus `core/config.py` erzeugt: `docs/generated/configuration.md`. Kurzfassung:

| Variable | Default | Bedeutung |
|---|---|---|
| `DATABASE_URL` | `postgresql+asyncpg://app:app@localhost:5432/app` | asyncpg-Treiber erforderlich |
| `APP_ENV` | `production` | `development` aktiviert `/docs`, `/openapi.json` und Console-Logs, Cookie `session` ohne `Secure` statt `__Host-session`; `production`/`test` → JSON-Logs. `mise run dev` und `compose.override.yaml` setzen `development` |
| `LOG_LEVEL` | `INFO` | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `DEFAULT_TIMEZONE` | `Europe/Berlin` | Zeitzone für die Auswertung von Kalenderdaten (Scheduler) |
| `UPLOADS_DIR` | `data/uploads` | Ablage für Bild-Uploads, in Produktion ein Volume |
| `SESSION_TTL_DAYS` | `14` | Lebensdauer einer Session, verlängert bei jeder Nutzung |
| `SESSION_MAX_LIFETIME_DAYS` | `30` | Höchstalter einer Session ab der Anmeldung, unabhängig von der Nutzung |
| `REGISTRATION_ENABLED` | `false` | `true` öffnet `POST /api/v1/auth/register` und die Seite `/register`; sonst 403 und kein Link im Frontend, das dieselbe Variable liest. Konten dann per `create-user` |

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

Immer Key-Value statt f-Strings – im JSON-Modus werden daraus filterbare Felder. Die `request_id` aus dem Header `x-request-id` (übernommen, wenn er `[A-Za-z0-9._-]{1,64}` entspricht, sonst eine neue UUID) hängt automatisch an jeder Zeile eines Requests. Uvicorn-, SQLAlchemy- und Alembic-Logs laufen durch denselben Renderer.

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
| `POST /api/v1/auth/register` | Konto anlegen, setzt Session-Cookie (201, 403 bei geschlossener Registrierung, 409 bei bekannter E-Mail) |
| `POST /api/v1/auth/login` | Anmelden, setzt Session-Cookie (401 bei falschen Daten) |
| `POST /api/v1/auth/logout` | Session widerrufen, Cookie löschen (204, idempotent) |
| `POST /api/v1/auth/logout-all` | Alle Sessions des Kontos auf allen Geräten widerrufen, Cookie löschen (204) |
| `GET /api/v1/auth/me` | Eigenes Konto (401 ohne gültige Session) |
| `DELETE /api/v1/auth/account` | Konto mit allen Daten löschen (204) |
| `GET /docs` | Swagger UI, nur `APP_ENV=development` |
| `GET /openapi.json` | Schema, nur `APP_ENV=development`; Export in jeder Umgebung: `mise run openapi` |
