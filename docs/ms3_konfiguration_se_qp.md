# Konfiguration der Softwareentwicklung und Qualitätsplanung

## Konfiguration der Softwareentwicklung

### Ausgangslage

Zu MS 3 stehen die technischen Grundlagen. Monorepo, Toolchain, Git-Hooks, CI-Pipeline, Container und das Grundgerüst von Backend und Frontend sind eingerichtet. Ein Health-Endpunkt prüft die Datenbankverbindung. Die Authentifizierung ist implementiert und wird mit MS 3 in `main` übernommen. Rate-Limit und Origin-Prüfung fehlen noch.

Das Datenmodell ist vollständig attributiert und für alle Entwickler verbindlich. Auf dieser Basis setzt das Team ab KW 40 die Fachdomänen parallel um.

### Vorgehensmodell

Das Team arbeitet iterativ in drei Abschnitten. Jeder endet mit einem lauffähigen, auf `main` zusammengeführten Stand:

| Abschnitt      | Zeitraum              | Ziel                                                                                                                                                       |
| -------------- | --------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Sprint 0       | bis 27.09.2026 (MS 3) | Entwicklungskonfiguration, Datenmodell, Authentifizierung übernehmen, Walking Skeleton unter HTTPS erreichbar                                              |
| Sprint 1       | 28.09. bis 03.10.2026 | Mandantentrennung als Pattern, erste Fachdomäne „Personen und Anlässe“ vollständig durch alle Schichten (Modell, Migration, Service, API, Tests, Frontend) |
| Sprint 2       | 04.10. bis 08.10.2026 | Geschenke, Beschenkungen, Aufgaben, Notizen, Anhänge, Benachrichtigungen, Teilen, HTML-Ansicht und Vorschläge parallel                                     |
| Stabilisierung | 09.10. bis 11.10.2026 | Feature-Freeze seit 08.10. Nur noch Fehlerbehebung, Tests, Dokumentation und Bereitstellung für MS 4                                                       |

Die erste Fachdomäne in Sprint 1 dient als Vorlage für alle weiteren. Die Stränge laufen erst parallel, wenn sie mit Tests und Frontend-Anbindung steht. Vier Personen schreiben dann gleichzeitig Modelle und Migrationen nach demselben Muster (Risiko TR-01).

Jeder Abschnitt beginnt mit dem Regelmeeting in Microsoft Teams. Dort werden Aufgaben verteilt und der Fortschritt gegen den Projektstrukturplan geprüft. Kurzfristige Blocker laufen über Signal. Die Qualitätsziele QZ-01 bis QZ-08 und die Definition of Done (siehe unten) sind die Abnahmekriterien jedes Abschnitts.

### Rollen und Zuständigkeiten in der Entwicklung

Die Rollen aus MS 1 gelten weiter. In der Entwicklung verteilen sich die Aufgaben so:

| Teammitglied       | Entwicklung                                                                                                                                                                                  | Review und Prüfung                                                                                                                                            |
| ------------------ | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Julian Ammann      | Frontend (SvelteKit) vollständig. Im Backend nur Authentifizierung und Sitzungsverwaltung (PSP 4.2). Initiale Einrichtung von Repository, Toolchain, CI/CD, Containern und Hosting (PSP 4.1) | Reviewt alle Backend-Pull-Requests. Pflicht-Reviewer (Code Owner) für Compose-Dateien, Dockerfiles, Workflows und Deploy-Konfiguration. Führt die Deploys aus |
| Kevin Jordan Taghu | Backend: Personen und Anlässe (PSP 4.3), Benachrichtigungen mit Scheduler und E-Mail-Versand (PSP 4.5), Teilen-Links und HTML-Darstellung (PSP 4.6)                                          | Reviewt Backend-Pull-Requests von Anton Hirsch. Koordiniert als Projektleitung die Abschnitte                                                                 |
| Anton Hirsch       | Backend: Geschenke, Beschenkungen, Aufgaben, Notizen und Anhänge (PSP 4.4), Geschenkideen-Vorschläge (PSP 4.7). Fachliche Testfälle und Rückverfolgbarkeit                                   | Reviewt Backend-Pull-Requests von Kevin Jordan Taghu. Prüft fachliche Korrektheit gegen die Anforderungen                                                     |
| Yin Yin Wu-Hanke   | Unterstützung im Frontend, Berechtigungs- und Sicherheitstests, Auswertung von Secret- und Abhängigkeitsscans                                                                                | Reviewt alle Frontend-Pull-Requests. Prüft sicherheitsrelevante Änderungen (Auth, Teilen-Links, Uploads)                                                      |

Für Reviews gilt: Backend-Code prüfen Julian Ammann und der jeweils andere Backend-Entwickler. Frontend-Code prüft Yin Yin Wu-Hanke. Die Auth-Änderungen von Julian Ammann im Backend prüfen Yin Yin Wu-Hanke (Sicherheit) und ein Backend-Entwickler. Niemand führt eigenen Code ohne fremde Freigabe zusammen.

Die Aufteilung nach Fachdomänen trennt die Backend-Stränge von Kevin Jordan Taghu und Anton Hirsch. Jede Domäne hat je eine Datei in jeder Schicht (`models/person.py`, `schemas/person.py`, `services/person.py`, `api/v1/persons.py`). Gemeinsam bearbeitet werden nur `models/__init__.py` und `api/v1/router.py`. Merge-Konflikte können so nur in diesen zwei Registrierungsdateien entstehen.

Backend und Frontend verbindet die OpenAPI-Spezifikation. Ein Backend-Endpunkt gilt erst als übergeben, wenn er mit `summary`, `description` und Beispielen im Schema erscheint. Das Frontend baut ausschließlich gegen die daraus generierten Typen.

### Architektur

```text
Browser ──HTTPS──▶ Traefik ──▶ Frontend (SvelteKit, Node, :3000)
                                    │
                                    │ load / Form Actions (serverseitig)
                                    │
                                    │ /api/* Proxy (Browser-Aufrufe)
                                    ▼
                                Backend (FastAPI, :8000) ──▶ PostgreSQL 17
                                    ▲                          ▲
                                    │                          │
                                Scheduler (gleiches Image) ────┘
                                    │
                                    ▼
                                SMTP-Dienst
```

* Nur das Frontend ist öffentlich erreichbar. Backend, Scheduler und Datenbank hängen nur am internen Netz `app-net`.
* Aus Sicht des Browsers gibt es nur eine Origin. Session-Cookies sind First-Party-Cookies, CORS entfällt.
* Der Scheduler läuft als eigener Prozess aus demselben Backend-Image, mit genau einer Instanz. Im API-Prozess läuft kein Scheduler.
* Bilddateien liegen auf einem eigenen Volume. Sie werden nur über einen authentifizierten API-Endpunkt ausgeliefert.

### Technologie-Stack

| Bereich                       | Festlegung                                                                    | Version         |
| ----------------------------- | ----------------------------------------------------------------------------- | --------------- |
| Backend-Sprache               | Python                                                                        | 3.14            |
| Web-Framework                 | FastAPI mit Uvicorn, vollständig asynchron                                    | ≥ 0.141         |
| Datenzugriff                  | SQLAlchemy 2.0 (async) mit asyncpg                                            | 2.x             |
| Datenbank                     | PostgreSQL                                                                    | 17              |
| Schemamigrationen             | Alembic mit asynchroner Umgebung                                              | ≥ 1.20          |
| Validierung und Konfiguration | Pydantic, pydantic-settings                                                   | 2.x             |
| Passwort-Hashing              | Argon2id über `pwdlib[argon2]`                                                | -               |
| Logging                       | structlog, Konsole lokal, JSON in Produktion, Request-ID pro Anfrage          | ≥ 26.1          |
| Scheduler (geplant)           | APScheduler in eigenem Prozess                                                | -               |
| E-Mail (geplant)              | aiosmtplib hinter `Mailer`-Protokoll, Mailpit lokal                           | -               |
| Bildverarbeitung (geplant)    | Pillow für Formatprüfung und EXIF-Entfernung                                  | -               |
| Frontend-Sprache              | TypeScript                                                                    | 6.x             |
| Frontend-Framework            | SvelteKit 2 mit Svelte 5 (Runes) und `adapter-node`, serverseitiges Rendering | 2.x / 5.x       |
| Styling                       | Tailwind CSS                                                                  | 4.x             |
| API-Client                    | `openapi-fetch` mit generierten Typen aus `openapi-typescript`                | 0.17 / 7.x      |
| Laufzeit Frontend             | Node.js                                                                       | 26              |
| Paketverwaltung               | uv (Backend), pnpm (Frontend)                                                 | 0.12.9 / 12.5.1 |
| Tests                         | pytest, pytest-asyncio, pytest-cov, httpx, testcontainers, Vitest, Playwright | -               |

Python 3.14, Node 26, TypeScript 6, Vite 8, ESLint 10 und Vitest 4 sind sehr neue Versionen. Lockfiles und gepinnte Werkzeuge begrenzen das Risiko. Tritt ein blockierender Fehler auf, geht das Team eine Major-Version zurück. Das Risiko ist als TR-05 in der Risikoliste zu ergänzen.

### Repository-Struktur

```text
isefgm/
├── backend
│   ├── alembic
│   │   └── versions
│   ├── src
│   │   └── giftmanager
│   │       ├── api
│   │       │   └── v1
│   │       ├── core
│   │       ├── models
│   │       ├── schemas
│   │       └── services
│   └── tests
├── docs
│   ├── ER-Modell
│   ├── images
│   │   └── team
│   ├── latex
│   ├── ms2
│   └── pdf
└── frontend
    ├── src
    │   ├── lib
    │   │   ├── api
    │   │   ├── assets
    │   └── routes
    │       └── api
    │           └── [...path]
    └── static
```

### Konfiguration des Backends

#### Schichten

| Schicht  | Verzeichnis | Verantwortung                                                             | Darf nicht                                                              |
| -------- | ----------- | ------------------------------------------------------------------------- | ----------------------------------------------------------------------- |
| API      | `api/v1/`   | HTTP-Routing, Auth-Dependency, Request- und Response-Schemas, Statuscodes | Geschäftslogik enthalten, direkt SQL formulieren                        |
| Schemas  | `schemas/`  | Validierung und Serialisierung mit Beschreibungen und Beispielen          | auf die Datenbank zugreifen                                             |
| Services | `services/` | Geschäftsregeln, Besitzerprüfung, Queries                                 | `HTTPException` werfen, `commit()` aufrufen, `datetime.now()` verwenden |
| Modelle  | `models/`   | Tabellen, Beziehungen, Constraints, Kommentare                            | Logik enthalten                                                         |

Imports sind durchgängig absolut (`from giftmanager.core.config import get_settings`). Relative Imports sind per Ruff verboten.

#### Verbindliche Regeln

Diese Regeln stehen im Backend-README. Sie werden in jedem Backend-Review geprüft.

1. **Transaktion.** `get_session` öffnet eine Transaktion pro Request. Rückkehr des Endpunkts führt zum Commit, eine Exception zum Rollback. Services rufen nur `flush()`. Ausnahme ist der Scheduler mit einer eigenen Transaktion pro Nachricht.

2. **Mandantentrennung (QZ-06).**

    * Jede kontogebundene Tabelle hat `owner_id` mit Fremdschlüssel auf `user_account.id`, `ON DELETE CASCADE` und Index.
    * Services erhalten `owner_id` als ersten Parameter und filtern jede Query damit. `session.get(Model, id)` ohne Besitzerfilter ist verboten.
    * Fremde IDs liefern `404`, nie `403`. Die Antwort verrät nicht, ob die Ressource existiert.
    * Beim Verknüpfen zweier Datensätze prüft der Service, dass beide demselben Konto gehören. Systemweite Anlasstypen (`owner_id IS NULL`) sind ausgenommen.
    * Zu jeder Ressource gehört ein Test „Nutzer B greift auf Ressource von Nutzer A zu → 404“.

3. **Fehler.** Fachfehler werden als Unterklasse von `DomainError` geworfen. Ein zentraler Handler übersetzt sie, Validierungsfehler und HTTP-Fehler in das einheitliche Problem-Details-Format (`type`, `title`, `status`, `detail`, optional `errors[]`).

4. **Listen (QZ-02).** Jeder Listen-Endpunkt nimmt `limit` (Standard 50, maximal 200) und `offset` und liefert `Page[T]` mit `items`, `total`, `limit`, `offset`. Beziehungen werden mit `selectinload` geladen, nicht in Schleifen.

5. **Zeit.** Zeitpunkte werden als `timestamptz` in UTC gespeichert, Kalenderdaten als `date`. Die aktuelle Zeit kommt immer über `ClockDep`. Tests können damit ein festes Datum setzen, zum Beispiel für Weihnachtsbenachrichtigungen. Kalenderauswertungen laufen in `DEFAULT_TIMEZONE=Europe/Berlin`.

6. **Dokumentation.** Jede Tabelle und Spalte hat `comment=`. Jeder Endpunkt hat `summary` und `description`, jedes Schema-Feld `description` und `examples`. Jeder Test trägt `@pytest.mark.requirement(...)` mit den Anforderungs-IDs aus MS 1. Diese Texte sind Deutsch, Code und Kommentare Englisch.

#### API-Konventionen

* Präfix `/api/v1`, Ressourcen im Plural (`/persons`, `/gifts`, `/giftings`, `/tasks`).
* Jeder Endpunkt hat eine `operation_id` in camelCase (`listPersons`, `createGift`). Sie wird zum Methodennamen im generierten Client.
* Schreibende Endpunkte geben die vollständige Ressource zurück. Nur `DELETE` antwortet mit `204`.
* Statuswerte sind englische Enums (`idea`, `planned`, `acquired`, `given`). Die Übersetzung erfolgt im Frontend.
* Kalenderdaten im Format `YYYY-MM-DD`, Zeitpunkte als ISO 8601 mit Zeitzone.

#### Authentifizierung und Sitzungen

Alle fachlichen Endpunkte setzen eine Anmeldung voraus. Julian Ammann setzt die Authentifizierung im Backend und im Frontend um.

| Aspekt                  | Festlegung                                                                                                                                                                                           |
| ----------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Passwörter              | Argon2id über `pwdlib`, Länge 8 bis 128 Zeichen                                                                                                                                                      |
| Anmeldename             | E-Mail-Adresse, in Kleinbuchstaben gespeichert, eindeutig                                                                                                                                            |
| Sitzung                 | Tabelle `user_session` mit `token_hash`, `created_at`, `expires_at`, `last_seen_at`. In der Datenbank steht nur der SHA-256-Hash des Tokens, das Klartext-Token nur im Cookie                        |
| Cookie                  | `session`, `HttpOnly`, `SameSite=Lax`, `Path=/`, `Secure` außerhalb der Entwicklung. Laufzeit 14 Tage, Verlängerung bei Nutzung                                                                      |
| Zeitkonstante Anmeldung | Bei unbekannter E-Mail wird gegen einen Dummy-Hash geprüft. Die Antwortzeit verrät nicht, ob ein Konto existiert                                                                                     |
| Dependency              | `CurrentUser` in `core/auth.py`, auf Router-Ebene eingehängt. Fehlendes oder ungültiges Cookie führt zu `401`                                                                                        |
| Endpunkte               | `POST /auth/register`, `POST /auth/login`, `POST /auth/logout`, `GET /auth/me`, `DELETE /auth/account` (F-17)                                                                                        |
| Kontolöschung           | Löscht das Konto. Sitzungen und alle kontogebundenen Daten kaskadieren über `owner_id`                                                                                                               |
| Offen                   | Rate-Limit auf Login und Registrierung (10 Versuche je E-Mail in 15 Minuten, Tabelle `login_attempt`). Prüfung des `Origin`-Headers im Backend bei zustandsändernden Browser-Aufrufen über den Proxy |

Neun automatisierte Tests decken Registrierung, doppelte E-Mail, Passwortlänge, falsches Passwort, unbekanntes Konto, Anmeldung, Abmeldung mit Widerruf, abgelaufene Sitzung, Kontolöschung und Zugriff ohne Cookie ab.

#### Datenmodell und Migrationen

Das verbindliche Datenmodell steht in `docs/datenmodell.md` als Mermaid-ER-Diagramm. Es ersetzt das unvollständige yEd-Modell und ist mit dem Zielmodell aus MS 1 abgeglichen. Es enthält die zentrale Entität `gifting` (Beschenkung), die Zuordnungstabellen, `note`, `user_profile` und das Attribut `gift.category` für das Vorschlagsverfahren (F-16).

Konventionen:

* Primärschlüssel `id` als UUIDv7.
* Tabellen `user_account` und `user_session`, weil `user` in PostgreSQL reserviert ist.
* Statuswerte als String-Enums mit `CHECK`-Constraint: Beschenkung `idea | planned | acquired | given`, Aufgabe `open | in_progress | done | discarded`, Benachrichtigung `planned | sending | sent | failed`.
* Constraint-Namen nach fester Konvention (`pk_`, `fk_`, `uq_`, `ix_`, `ck_`). Migrationen bleiben damit deterministisch.
* Wiederkehrende Anlässe speichern die Regel. Die Beschenkung speichert den konkreten Termin (`gifting.occasion_date`).
* Systemweite Anlasstypen „Geburtstag“ und „Weihnachten“ werden per Daten-Migration angelegt.

Ablauf einer Schemaänderung:

1. Modell unter `models/<domäne>.py` anlegen und in `models/__init__.py` registrieren.
2. Migration mit `mise run migration -- "<beschreibung>"` erzeugen.
3. Migration gegenlesen. Autogenerate erkennt keine Umbenennungen und keine Datenänderungen.
4. `mise run migrate` und `mise run migrate:check`. Erwartet wird „No new upgrade operations detected“.
5. Im Review prüft Julian Ammann Migration und Modell gegen `docs/datenmodell.md`.

`alembic/env.py` vergleicht auch Server-Defaults. In Produktion führt der `migrate`-Container die Migrationen vor dem Start der API aus.

#### Scheduler, E-Mail und Bilder (Kevin Jordan Taghu und Anton Hirsch)

Diese Teile entstehen in Sprint 2. Das Team bestätigt die folgenden Festlegungen bis zum 27.09.2026:

* **Scheduler (PSP 4.5).** Einstiegspunkt `python -m giftmanager.scheduler`. Zwei Schritte: *Planen* legt Zeilen per `INSERT … ON CONFLICT DO NOTHING` an, *Versenden* holt fällige Zeilen mit `FOR UPDATE SKIP LOCKED` ab. Die Deduplizierung sichert der `UNIQUE`-Constraint auf `dedup_key` (Konto, Bezug, Ereignistermin, Typ, Intervall). Ein doppelt gestarteter Scheduler verschickt damit nichts doppelt (QZ-05). Zeilen, die länger als 15 Minuten im Status `sending` stehen, werden nicht automatisch wiederholt und als Warnung protokolliert.
* **E-Mail (PSP 4.5).** Protokoll `Mailer` mit `SmtpMailer` für Produktion, Mailpit für Entwicklung und E2E-Tests, `RecordingMailer` für Unit-Tests. Tests und Demos schreiben keine echten Adressen an. Der Anbieter für Produktion ist noch offen. Zur Auswahl stehen Brevo, Resend und Mailgun, als Rückfallebene der SMTP-Zugang eines Teammitglieds.
* **Bilder (PSP 4.4).** Speicherung unter `/data/uploads/<owner_id>/<uuid>.<ext>`, Metadaten in `attachment`. Erlaubt sind JPEG, PNG und WebP bis 5 MB. Die Prüfung erfolgt über den Dateiinhalt, nicht über die Endung. Ein Re-Encode entfernt EXIF-Daten. Ausgeliefert wird nur über `GET /api/v1/attachments/{id}/file` mit Sitzung oder gültigem Teilen-Token. Nach einer Kontolöschung werden die Dateien entfernt.

### Konfiguration des Frontends (Julian Ammann)

#### Datenfluss

```text
Browser ──▶ SvelteKit (Node, :3000) ──▶ FastAPI (:8000)
              │
              ├─ load / Form Actions: locals.api → event.fetch → handleFetch → API_URL
              │
              └─ Browser-Aufrufe auf /api/* → routes/api/[...path] (Proxy) → API_URL
```

#### Verbindliche Regeln

1. Daten werden nur serverseitig geladen, in `+page.server.ts` oder `+layout.server.ts` über `load`, mit `locals.api`. Der Client ist an das request-gebundene `fetch` gebunden. Ein globaler API-Client ist verboten, weil er beim serverseitigen Rendern bricht.

2. Schreibende Aktionen sind Form Actions mit `use:enhance`. Sie funktionieren ohne JavaScript und per Tastatur. Das unterstützt QZ-04 (Benutzbarkeit, Accessibility).

3. Fehler kommen vom Backend im Problem-Details-Format. `problemMessage()` übersetzt sie, `fail()` gibt sie an das Formular zurück. Fehlermeldungen erscheinen mit `role="alert"`. Eine Root-Fehlerseite `+error.svelte` fängt unerwartete Fehler.

4. Typen stammen nur aus der generierten `schema.d.ts`. Die Datei wird nie von Hand bearbeitet.

5. Statuswerte aus der API werden im Frontend ins Deutsche übersetzt.

#### Routen und Sitzung

| Route                             | Zweck                                             | Schutz                                                                             |
| --------------------------------- | ------------------------------------------------- | ---------------------------------------------------------------------------------- |
| `(auth)/login`, `(auth)/register` | Anmeldung und Registrierung als Form Actions      | öffentlich, angemeldete Nutzer werden auf `/` geleitet                             |
| `(app)/`                          | Übersicht und alle fachlichen Seiten              | Guard in `(app)/+layout.server.ts`, ohne Sitzung Weiterleitung auf `/login?next=…` |
| `(app)/account`                   | Konto anzeigen und löschen (F-17)                 | geschützt                                                                          |
| `logout`                          | Sitzung widerrufen, Cookie löschen                | nur Action                                                                         |
| `api/[...path]`                   | Weiterleitung von Browser-Aufrufen an das Backend | Cookie wird durchgereicht                                                          |

`hooks.server.ts` löst das Session-Cookie pro Request über `/api/v1/auth/me` in `locals.user` auf. Form Actions rufen das Backend serverseitig auf. `forwardSessionCookie()` überträgt das vom Backend gesetzte Cookie auf die SvelteKit-Antwort. `safeNext()` erlaubt nach dem Login nur Weiterleitungen auf eigene Pfade und verhindert Open Redirects. Security-Header (`X-Content-Type-Options`, `Referrer-Policy`, `X-Frame-Options`) setzt ebenfalls `hooks.server.ts`.

Fachliche Seiten entstehen in derselben Reihenfolge wie die Backend-Domänen. Das Frontend beginnt mit einer Domäne, sobald ihre Endpunkte in `openapi.json` stehen. Bis dahin baut es gegen den dokumentierten Schema-Entwurf.

### Entwicklungsumgebung

Jedes Teammitglied nutzt die eigene IDE. Reproduzierbar bleibt die Umgebung, weil mise alle Werkzeugversionen in `mise.toml` pinnt:

| Werkzeug | Version |
| -------- | ------- |
| Python   | 3.14    |
| Node.js  | 26.9.0  |
| pnpm     | 12.5.1  |
| uv       | 0.12.9  |
| Lefthook | 2.1.14  |
| gitleaks | 8.30.1  |

Zusätzlich braucht es Docker mit Compose. Eingerichtet wird die Umgebung so:

```sh
git clone https://github.com/julianammann/isefgm.git && cd isefgm

mise trust && mise install      # Toolchain
mise run setup                  # uv sync, pnpm install, lefthook install
cp .env.example .env
mise run db                     # PostgreSQL-Container
mise -C backend run migrate
mise -C backend run dev         # http://localhost:8000/docs
mise -C frontend run dev        # http://localhost:3000
```

| Task                                   | Zweck                                                    |
| -------------------------------------- | -------------------------------------------------------- |
| `mise run check`                       | Lint, Typprüfung und Tests für Backend und Frontend      |
| `mise run openapi`                     | OpenAPI-Schema exportieren und TypeScript-Typen erzeugen |
| `mise run docs`                        | Dokumentation nach `docs/generated/` erzeugen            |
| `mise run docker`                      | Images mit gepinnter uv-Version bauen                    |
| `mise -C backend run migration -- "…"` | neue Migration erzeugen                                  |

Lokal ergänzt `compose.override.yaml` die Basisdatei um Build-Kontexte, Ports (5432, 8000, 3000) und `APP_ENV=development`. Compose lädt die Datei automatisch, das Deploy ignoriert sie. Für VS Code liegen gemeinsame Einstellungen und Erweiterungsempfehlungen unter `.vscode/`.

### Versionsverwaltung, Branching und Review

* `main` ist durch das Regelwerk Main-Branch-Protection geschützt. Änderungen erfolgen nur per Pull Request mit mindestens einer Freigabe. Force-Pushes und das Löschen des Branches sind gesperrt.
* Zusätzlich ist „Require review from Code Owners“ aktiv. `.github/CODEOWNERS` macht Julian Ammann zum Pflicht-Reviewer für `compose*.yaml`, beide Dockerfiles, `.github/` und `deploy/`. Diese Dateien bestimmen, was auf dem Produktionsserver läuft.
* Branches sind kurzlebig und folgen dem Schema `feature/<domäne>-<thema>`, `fix/<thema>`, `docs/<thema>` oder `chore/<thema>`.
* Commit-Nachrichten folgen Conventional Commits mit Komponente als Scope: `feat(backend): …`, `fix(frontend): …`, `docs(ms3): …`.
* Ein Pull Request enthält eine Domäne oder ein Thema. Er wird zusammengeführt, wenn die CI grün ist, die Reviews laut Rollentabelle vorliegen und alle Anmerkungen bearbeitet sind.

### Lokale Qualitätssicherung über Git-Hooks

| Hook         | Prüfung                                                                                         | Komponente         |
| ------------ | ----------------------------------------------------------------------------------------------- | ------------------ |
| `pre-commit` | Ruff Lint mit Auto-Fix und Ruff Format                                                          | Backend            |
| `pre-commit` | ESLint mit Auto-Fix und Prettier                                                                | Frontend           |
| `pre-commit` | OpenAPI-Export und Neugenerierung der TypeScript-Typen bei Änderungen an `api/` oder `schemas/` | Backend → Frontend |
| `pre-commit` | gitleaks-Scan der gestagten Dateien                                                             | gesamt             |
| `pre-push`   | Pyright im Strict-Modus                                                                         | Backend            |
| `pre-push`   | `alembic check` auf fehlende Migrationen                                                        | Backend            |
| `pre-push`   | `svelte-check`                                                                                  | Frontend           |

Hooks lassen sich lokal umgehen. Die CI wiederholt deshalb alle Prüfungen.

### Continuous Integration

GitHub Actions führt die Prüfungen pfadgefiltert aus. Ein Platzhalter-Workflow meldet die Pflichtprüfungen bei reinen Dokumentationsänderungen als erfolgreich, damit die Branch Protection nicht blockiert.

| Workflow       | Auslöser                                     | Prüfungen                                                                                                                                                                                            |
| -------------- | -------------------------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| `backend.yml`  | Änderungen unter `backend/`                  | Ruff, Pyright (strict), Migrationen gegen PostgreSQL 17 anwenden und auf Vollständigkeit prüfen, pytest mit Coverage, Abgleich `frontend/openapi.json` mit dem Backend-Code, pip-audit (blockierend) |
| `frontend.yml` | Änderungen unter `frontend/`                 | Aktualität der generierten Typen gegenüber `openapi.json`, Prettier, ESLint, svelte-check, Vitest mit Playwright (Chromium), Build, pnpm audit (blockierend)                                         |
| `docker.yml`   | Änderungen an Backend oder Frontend          | Image-Build beider Komponenten, Push nach GHCR bei `main` und Tags `v*`                                                                                                                              |
| `gitleaks.yml` | jeder Push auf `main` und jeder Pull Request | Secret-Scan über die gesamte Historie                                                                                                                                                                |

Der API-Vertrag ist damit in beide Richtungen abgesichert. Die Backend-CI prüft, dass das Schema zum Code passt. Die Frontend-CI prüft, dass die Typen zum Schema passen. Alle Workflows laufen mit minimalen Berechtigungen (`contents: read`), nur der Docker-Workflow zusätzlich mit `packages: write`. Die CI verwendet dieselbe `mise.toml` wie die lokale Umgebung.

### Abhängigkeiten

* Backend-Abhängigkeiten sind in `pyproject.toml` deklariert und in `uv.lock` fixiert, Frontend-Abhängigkeiten in `package.json` und `pnpm-lock.yaml`. Die CI installiert nur aus den Lockfiles (`--frozen`).
* Entwicklungswerkzeuge liegen in getrennten Dev-Gruppen und gelangen nicht in die Produktions-Images.
* Dependabot (`.github/dependabot.yml`) prüft wöchentlich uv, npm, GitHub Actions und Docker-Basis-Images. Updates kommen gruppiert als Pull Request.
* `pip-audit` und `pnpm audit` brechen den Build bei bekannten Schwachstellen ab (QZ-06).

### Konfiguration und Geheimnisse

Die Laufzeitkonfiguration kommt nur aus Umgebungsvariablen, die pydantic-settings typisiert einliest. Jedes Feld hat eine Beschreibung, aus der die Konfigurationstabelle der Betriebsdokumentation erzeugt wird.

| Variable             | Standard                | Bedeutung                                                                                         |
| -------------------- | ----------------------- | ------------------------------------------------------------------------------------------------- |
| `APP_ENV`            | `development`           | `development` aktiviert `/docs` und Konsolen-Logs, `production` und `test` schalten auf JSON-Logs |
| `LOG_LEVEL`          | `INFO`                  | `DEBUG`, `INFO`, `WARNING`, `ERROR`                                                               |
| `DATABASE_URL`       | lokale Entwicklungs-DB  | PostgreSQL mit asyncpg-Treiber                                                                    |
| `DEFAULT_TIMEZONE`   | `Europe/Berlin`         | Zeitzone für Kalenderauswertungen                                                                 |
| `UPLOADS_DIR`        | `/data/uploads`         | Ablage der Bilddateien                                                                            |
| `SESSION_TTL_DAYS`   | `14`                    | Laufzeit einer Sitzung                                                                            |
| `API_URL` (Frontend) | `http://localhost:8000` | Backend-Adresse für `handleFetch` und Proxy                                                       |
| `ORIGIN` (Frontend)  | keiner                  | öffentliche Origin, nötig für Form Actions in Produktion                                          |

Regeln für Geheimnisse:

* `.env`-Dateien sind über `.gitignore` ausgeschlossen. `.env.example` enthält nur unkritische Entwicklungswerte.
* gitleaks prüft vor jedem Commit und in der CI über die gesamte Historie.
* Produktionsgeheimnisse (Datenbankzugang, SMTP-Zugang) liegen nicht im Projekt-Repository. Sie liegen als verschlüsselte Environment-Secrets im separaten Infrastruktur-Repository und werden beim Deploy eingespielt.
* Testkonten und Zugangsdaten für den Tutor werden nur über Redmine übergeben.

### Teststrategie

| Ebene                         | Werkzeug                                  | Umfang                                                                                                                                                                   | Verantwortlich              |
| ----------------------------- | ----------------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | --------------------------- |
| Unit Backend                  | pytest, `RecordingMailer`, Fake-Clock     | Services, Scheduler-Planung, Vorschlagslogik                                                                                                                             | Entwickler der Domäne       |
| Integration Backend           | pytest, httpx, testcontainers             | jeder Endpunkt: Normalfall, Validierung, Fremdzugriff → 404. Echter PostgreSQL-17-Container, alle Migrationen eingespielt, jeder Test in einem zurückgerollten Savepoint | Entwickler der Domäne       |
| Berechtigung                  | wie Integration                           | Mandantentrennung je Ressource, Teilen-Link zeigt nur freigegebene Personen                                                                                              | Yin Yin Wu-Hanke            |
| Unit und Komponenten Frontend | Vitest, `vitest-browser-svelte`, Chromium | Hilfsfunktionen (Session, Weiterleitung, Fehler-Mapping), Komponenten                                                                                                    | Julian Ammann               |
| End-to-End                    | Playwright gegen den Compose-Stack        | 4 bis 6 Kernabläufe: registrieren, Person anlegen, Idee → Beschenkung → verschenkt, Teilen-Link öffnen, Konto löschen. Mehrere Browser-Engines (QZ-08)                   | Julian Ammann, Anton Hirsch |
| Last                          | Seed-Skript mit synthetischem Testbestand | Nachweis QZ-02, Messwerte in den Testabschlussbericht                                                                                                                    | Anton Hirsch                |

* `pytest-cov` misst die Abdeckung bei jedem Lauf. Das Ziel aus QZ-07 sind mindestens 70 % Zeilenabdeckung im Backend.
* `--strict-markers` lehnt falsch geschriebene Marker ab. Warnungen gelten in pytest als Fehler.
* Jeder Test trägt `@pytest.mark.requirement("F-xx", "Q-xx")`. Jeder vollständige pytest-Lauf schreibt die Rückverfolgbarkeitsmatrix `docs/generated/rueckverfolgbarkeit.md` (Anforderung ↔ Test ↔ Ergebnis). Das ist der Nachweis für QZ-01.
* E2E-Tests laufen in einem eigenen Workflow nur auf `main` und vor Releases, damit Pull Requests schnell bleiben.

### Bereitstellung und Betrieb

#### Container

| Image                                  | Basis              | Merkmale                                                                                                                              |
| -------------------------------------- | ------------------ | ------------------------------------------------------------------------------------------------------------------------------------- |
| `ghcr.io/julianammann/isefgm/backend`  | `python:3.14-slim` | Multi-Stage mit uv, Nicht-Root-Benutzer, nur Produktionsabhängigkeiten, Port 8000. Dient auch als Image für `migrate` und `scheduler` |
| `ghcr.io/julianammann/isefgm/frontend` | `node:26-alpine`   | Multi-Stage mit pnpm, Benutzer `node`, Port 3000                                                                                      |

Images werden mit Branch, Pull Request, Commit-SHA und bei Releases mit der SemVer-Version getaggt.

#### Compose-Dateien

| Datei                     | Inhalt                                                                                                                                                                                                                         |
| ------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| `compose.yaml`            | Basis: Dienste `db`, `migrate`, `api`, `scheduler` (per Profil, bis der Scheduler existiert), `frontend`. Health-Checks, internes Netz `app-net`, Volumes `pgdata` und `uploads`, `no-new-privileges`. Keine Ports, kein Build |
| `compose.override.yaml`   | nur lokal: Build-Kontexte, Ports, Development-Modus                                                                                                                                                                            |
| `compose.production.yaml` | Produktion: Frontend am Traefik-Netz mit Router-Labels auf die Domain, Speicher- und CPU-Limits für alle Dienste                                                                                                               |

Health-Checks steuern die Startreihenfolge: Die API startet erst nach erfolgreicher Migration, das Frontend erst bei gesunder API. `/api/v1/health/live` und `/api/v1/health/ready` melden Prozess- und Datenbankzustand.

#### Hosting

Das System läuft auf einem bestehenden, gehärteten Server eines Teammitglieds. Traefik übernimmt dort Routing, TLS mit Let's Encrypt, HSTS, Security-Header und Rate-Limit am Eingang. Auch Firewall, Monitoring und Log-Sammlung stellt der Server. Das Projekt liefert nur seine Compose-Dateien.

Julian Ammann stößt das Deploy zentral im separaten Infrastruktur-Repository an, sobald der `docker`-Workflow grün ist. Deployt wird immer mit vollem Commit-SHA und dem dazu gebauten Image-Tag, nie mit `main`. Im öffentlichen Projekt-Repository liegen damit keine Deploy-Credentials.

Vor jedem Deploy lehnen automatische Gates Ports, Bind-Mounts und fremde Netze im Stack ab. Lokal lässt sich das mit `docker compose -f compose.yaml -f compose.production.yaml config` vorab prüfen.

Schon in Sprint 0 ist die leere Anwendung mit Health-Endpunkt als Walking Skeleton unter HTTPS erreichbar. Deployment-Probleme sollen nicht erst kurz vor MS 4 auffallen.

Der Stack verarbeitet nur synthetische Testdaten, ein Offsite-Backup gibt es nicht. Nach einem Datenverlust spielt ein Seed-Skript Testkonten und Testbestand neu ein. Dieses Skript muss deshalb existieren, bevor das System dem Tutor bereitgestellt wird.

Die öffentliche Domain legt das Team in Sprint 0 fest und trägt sie in die Betriebsdokumentation ein.

### Definition of Done

Ein Endpunkt beziehungsweise eine Funktion ist fertig, wenn alle Punkte erfüllt sind:

**Backend**

* [ ] Tabelle entspricht `docs/datenmodell.md`, Migration erzeugt, gegengelesen und `alembic check` grün
* [ ] jede Tabelle und Spalte hat `comment=`
* [ ] Service erhält `owner_id` und filtert jede Query damit, Fachfehler als `DomainError`
* [ ] Router mit `CurrentUser`, `operation_id`, `summary`, `description`; Schema-Felder mit `description` und `examples`
* [ ] Listen paginiert mit `Page[T]`
* [ ] Tests für Normalfall, Validierung und Fremdzugriff → 404, jeder mit `requirement`-Marker
* [ ] `mise run openapi` und `mise run docs` ausgeführt, generierte Dateien committet

**Frontend**

* [ ] Daten per `load` über `locals.api`, Mutationen als Form Action
* [ ] Fehlerzustände sichtbar und per Screenreader angekündigt, ohne JavaScript bedienbar
* [ ] Typen nur aus `schema.d.ts`, Lint, `svelte-check` und Vitest grün

**Gemeinsam**

* [ ] CI grün, Review laut Rollentabelle freigegeben
* [ ] betroffene Anforderung in der Rückverfolgbarkeitsmatrix mit `passed`

## Konfiguration der Liefergegenstände

### Liefergegenstände und Zuständigkeiten

Jeder Liefergegenstand hat eine Kennung, eine verantwortliche und eine prüfende Person sowie einen festen Ablageort. Die prüfende Person ist nie die verantwortliche Person.

| ID    | Liefergegenstand                                                              | MS | Format                                    | Ablage                                                                                                    | Verantwortlich                                                      | Prüfend            |
| ----- | ----------------------------------------------------------------------------- | -- | ----------------------------------------- | --------------------------------------------------------------------------------------------------------- | ------------------------------------------------------------------- | ------------------ |
| LG-01 | Konfiguration der Softwareentwicklung und Qualitätsplanung                    | 3  | Markdown → PDF                            | `docs/ms3_konfiguration_se_qp.md`, `docs/datenmodell.md`                                                  | Julian Ammann                                                       | Kevin Jordan Taghu |
| LG-02 | Programmcode Backend                                                          | 4  | Git-Repository                            | `backend/`                                                                                                | Kevin Jordan Taghu, Anton Hirsch (Auth: Julian Ammann)              | Julian Ammann      |
| LG-03 | Programmcode Frontend                                                         | 4  | Git-Repository                            | `frontend/`                                                                                               | Julian Ammann                                                       | Yin Yin Wu-Hanke   |
| LG-04 | Lauffähiges System (Link)                                                     | 4  | Container-Images, URL                     | GHCR, Produktionsserver                                                                                   | Julian Ammann                                                       | Anton Hirsch       |
| LG-05 | Benutzerhandbuch                                                              | 4  | Markdown → PDF, Screenshots aus E2E-Tests | `docs/ms4/benutzerhandbuch.md`, `docs/handbuch/`                                                          | Yin Yin Wu-Hanke                                                    | Anton Hirsch       |
| LG-06 | Fachliche Dokumentation: Prozesse, Konzepte, Geschäftsregeln                  | 4  | Markdown → PDF                            | `docs/ms4/fachliche_dokumentation.md`                                                                     | Anton Hirsch                                                        | Kevin Jordan Taghu |
| LG-07 | Technische Dokumentation: Architektur, Komponenten, Schnittstellen, Datenbank | 4  | Markdown, teilweise generiert             | `docs/ms4/technische_dokumentation.md`, `docs/generated/schnittstellen.md`, `docs/generated/datenbank.md` | Julian Ammann (Architektur, Frontend), Kevin Jordan Taghu (Backend) | Anton Hirsch       |
| LG-08 | Betriebsdokumentation: Installation, Konfiguration, Admin-Account             | 4  | Markdown, teilweise generiert             | `deploy/README.md`, `docs/generated/konfiguration.md`, `README.md`                                        | Julian Ammann                                                       | Kevin Jordan Taghu |
| LG-09 | Testabschlussbericht mit Testfällen und Testprotokollen                       | 4  | Markdown → PDF, CI-Protokolle             | `docs/ms4/testabschlussbericht.md`, `docs/generated/rueckverfolgbarkeit.md`                               | Anton Hirsch                                                        | Yin Yin Wu-Hanke   |
| LG-10 | Liste der Testkonten und Zugangsdaten                                         | 4  | PDF                                       | nur Redmine, nie im Repository                                                                            | Yin Yin Wu-Hanke                                                    | Julian Ammann      |
| LG-11 | Ergebnispräsentation                                                          | 5  | Video oder Link                           | `docs/ms5/` (Folien)                                                                                      | Kevin Jordan Taghu                                                  | Anton Hirsch       |
| LG-12 | Gemeinsamer Projektbericht                                                    | 6  | PDF                                       | `docs/ms6/`                                                                                               | Kevin Jordan Taghu                                                  | alle               |

### Herkunft der Inhalte

MS 4 verlangt acht Liefergegenstände, davon fünf Dokumente. Ein großer Teil davon lässt sich aus dem Code erzeugen, wenn die Fakten schon beim Schreiben dort stehen. Sonst müsste das Team die gesamte Dokumentation in KW 41 nachziehen.

| Liefergegenstand                          | Quelle                                                                | Erzeugt durch                                                                            | Anteil aus Code  |
| ----------------------------------------- | --------------------------------------------------------------------- | ---------------------------------------------------------------------------------------- | ---------------- |
| Technische Doku: Schnittstellen           | `summary`, `description`, `Field(description=)`, `OPENAPI_TAGS`       | `mise run docs` → `docs/generated/schnittstellen.md`, dazu `openapi.json` und Swagger UI | fast vollständig |
| Technische Doku: Datenbank                | `comment=` an Tabellen und Spalten                                    | `mise run docs` → `docs/generated/datenbank.md`, Beziehungen in `docs/datenmodell.md`    | weitgehend       |
| Technische Doku: Architektur, Komponenten | Backend- und Frontend-README                                          | von Hand                                                                                 | teilweise        |
| Betriebsdoku: Konfiguration               | `Field(description=)` in `Settings`                                   | `mise run docs` → `docs/generated/konfiguration.md`                                      | vollständig      |
| Betriebsdoku: Installation, Admin-Account | `compose*.yaml`, `deploy/README.md`, Seed-Skript                      | von Hand                                                                                 | teilweise        |
| Testabschlussbericht                      | `requirement`-Marker, pytest, pytest-cov, Vitest, Playwright          | pytest → `docs/generated/rueckverfolgbarkeit.md`, Coverage-Ausgabe, CI-Protokolle        | vollständig      |
| Fachliche Doku: Geschäftsregeln           | Docstrings der Services, `DomainError`-Texte, fachlich benannte Tests | von Hand                                                                                 | teilweise        |
| Fachliche Doku: Prozesse, Konzepte        | keine                                                                 | von Hand, Mermaid-Sequenzdiagramme, Glossar                                              | kaum             |
| Benutzerhandbuch                          | Playwright-Screenshots                                                | Text von Hand, Screenshots aus den E2E-Tests                                             | kaum             |

Die Dateien unter `docs/generated/` werden committet, damit sie ohne Toolchain lesbar sind und Änderungen im Pull-Request-Diff erscheinen. Von Hand bearbeitet werden sie nie, darauf weist die erste Zeile jeder Datei hin. Vor dem Commit läuft einmal der vollständige Testlauf, weil ein Teillauf die Matrix mit einem Teilstand überschreibt.

Die Playwright-Abläufe legen Screenshots für das Benutzerhandbuch unter `docs/handbuch/<ablauf>-<schritt>.png` ab. Ändert sich die Oberfläche, entstehen die Bilder beim nächsten Lauf neu.

### Identifikation und Versionierung

* Dokumente liegen unter `docs/` und heißen `ms<Nummer>_<thema>.md`. Ab MS 4 erhält jeder Meilenstein einen Unterordner `docs/ms<Nummer>/`. Bilder liegen unter `docs/images/`. Dateinamen sind durchgehend klein geschrieben, sonst brechen Links auf case-sensitiven Systemen.
* PDF-Abgabefassungen werden aus den Markdown-Quellen beziehungsweise aus `docs/latex/` erzeugt und unter `docs/pdf/` abgelegt. Sie sind abgeleitete Kopien. Änderungen erfolgen immer in der Quelle.
* Die Software folgt Semantic Versioning. Die Version steht in `backend/pyproject.toml` und `frontend/package.json`, derzeit `0.1.0`. Die für MS 4 abgegebene Fassung erhält den Tag `v1.0.0`. Der Tag löst Build und Veröffentlichung der Images mit derselben Versionsnummer aus. Korrekturen nach Tutorfeedback erhöhen die Patch-Version (`v1.0.1`).
* Abgabestände werden als Git-Tag `ms<Nummer>-abgabe` markiert. Der eingereichte Stand bleibt damit reproduzierbar, auch wenn `main` weiterentwickelt wird.

### Baselines je Meilenstein

| Baseline | Inhalt                                                                                                                      | Kennzeichnung                                           |
| -------- | --------------------------------------------------------------------------------------------------------------------------- | ------------------------------------------------------- |
| MS 3     | Konfigurationsdokument, Datenmodell, Entwicklungsumgebung, CI-Pipeline, Grundgerüst mit Authentifizierung, Walking Skeleton | Tag `ms3-abgabe`                                        |
| MS 4     | Programmcode, Container-Images, Dokumentation LG-05 bis LG-09, generierte Dokumente                                         | Tags `v1.0.0` und `ms4-abgabe`, Images `:1.0.0` in GHCR |
| MS 5     | Präsentation auf Basis der MS-4-Baseline                                                                                    | Tag `ms5-abgabe`                                        |
| MS 6     | Projektbericht                                                                                                              | Tag `ms6-abgabe`                                        |

Nach einer Baseline ändert sich der abgegebene Stand nur über einen neuen Pull Request und eine neue Version.

### Änderungs- und Freigabeprozess

1. Die verantwortliche Person erstellt oder ändert den Liefergegenstand in einem eigenen Branch.
2. Sie öffnet einen Pull Request gegen `main`. Die prüfende Person reviewt Inhalt, Form und Vollständigkeit gegen die Qualitätsziele und die Definition of Done.
3. Die CI muss grün sein. Bei Dokumenten ohne Codeänderung meldet der Platzhalter-Workflow die Pflichtprüfungen als erfolgreich.
4. Nach der Freigabe wird der Pull Request zusammengeführt. Die Abgabefassung wird erzeugt und der Stand getaggt.
5. Die Projektleitung lädt die Abgabe in Redmine hoch, setzt das Meilensteinticket auf **Feedback** und weist es dem Tutor zu.
6. Tutorfeedback wird am Redmine-Ticket festgehalten. Notwendige Korrekturen durchlaufen erneut die Schritte 1 bis 5. Der Tutor nimmt mit dem Status **closed** ab.

Die letzten zwei Tage vor jeder Abgabe sind für Review, Korrektur und Bereitstellung reserviert.

### Prüfverfahren für Liefergegenstände

| Liefergegenstand           | Prüfung                                                                                                                     |
| -------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| Programmcode               | CI grün (Lint, Typen, Tests, Audits, Secret-Scan), Review laut Rollentabelle, Definition of Done erfüllt                    |
| Lauffähiges System         | Deployment-Test aus leerem Zustand, Health-Endpunkte, E2E-Abläufe gegen die Produktions-URL, Anmeldung mit allen Testkonten |
| Generierte Dokumente       | erzeugt aus dem Release-Commit, Diff im Pull Request geprüft                                                                |
| Handgeschriebene Dokumente | eine nicht beteiligte Person liest den Text gegen den Code und zeichnet das im Pull Request ab                              |
| Testabschlussbericht       | Zahlen (Testanzahl, Coverage, Antwortzeiten) nur aus echten Läufen des Release-Commits, Matrix vollständig                  |
| Testkonten                 | Login mit jedem Konto vor Übergabe, keine Zugangsdaten im Repository (gitleaks)                                             |

### Schutz vertraulicher Liefergegenstände

Weil das Repository öffentlich ist, werden Zugangsdaten, Testkonten und Produktionsgeheimnisse nie versioniert. Testkonten gehen nur über Redmine an den Tutor (LG-10), Produktionsgeheimnisse liegen im separaten Infrastruktur-Repository. Der Prototyp verarbeitet nur synthetische Testdaten. gitleaks fängt lokal und in der CI Geheimnisse ab, die versehentlich in einen Commit geraten.

## Qualitätsplanung

### Qualitätsziele

Qualitätskriterien nach ISO/IEC 25010

| ID | Merkmal | Qualitätsziel | Prüfverfahren | Zeitpunkt / Verantwortlich |
| --- | --- | --- | --- | --- |
| QZ-01 | Funktionale Eignung | Alle als „Muss“ priorisierten Anforderungen sind umgesetzt und durch mindestens einen Testfall abgedeckt; 100 % der Muss-Testfälle sind bestanden. Berechnungen sind korrekt, z. B. enthält die Geburtstagsübersicht des Folgemonats genau die betroffenen Personen. Die Umwandlung einer Geschenkidee in ein Geschenk erfolgt in einem Schritt. | Rückverfolgbarkeitsmatrix Anforderung ↔ Testfall; Unit-, Integrations- und Systemtests | Je Sprint |
| QZ-02 | Leistungseffizienz | Listen werden bei einem Testbestand von 100 Personen, 1.000 Geschenkideen und 1.000 Beschenkungen in höchstens 2 Sekunden angezeigt (lokale Testumgebung, Q-05). | Lasttest mit generierten Testdaten, Messung im Browser | --- |
| QZ-03 | Kompatibilität | Der Frontend-Client entspricht der OpenAPI-Spezifikation des Backends (typisierter Client, keine Typfehler); der HTML-Export ist valides HTML. | Typprüfung in CI, W3C-Validator | --- |
| QZ-04 | Benutzbarkeit | Eine Geschenkidee kann ohne Anleitung in höchstens 3 Interaktionen und unter 30 Sekunden erfasst werden; Löschvorgänge erfordern eine Bestätigung; ungültige Eingaben erzeugen verständliche Fehlermeldungen; Lighthouse-Accessibility-Wert ≥ 90. | Usability-Test mit 3 Testpersonen außerhalb des Teams, Testfälle mit ungültigen Eingaben, Lighthouse-Audit | --- |
| QZ-05 | Zuverlässigkeit | Geburtstagsbenachrichtigungen und Weihnachts-Statusmeldungen werden zum vorgesehenen Zeitpunkt vollständig und ohne Duplikate erzeugt; der Ausfall eines externen Dienstes (E-Mail-Versand, KI-Ideengenerierung) beeinträchtigt die Kernfunktionen nicht; Container starten nach Neustart automatisch. | Scheduler-Test mit simulierter Systemzeit, Integrationstest mit simuliertem Ausfall, Neustart-Test | --- |
| QZ-06 | Sicherheit | Nutzende können ausschließlich auf eigene Daten zugreifen; Passwörter werden nur gehasht gespeichert; geteilte Links sind nicht erratbar und widerrufbar; keine Schwachstellen mit Schweregrad kritisch oder hoch in Abhängigkeiten und Images; keine Secrets im Repository; im Prototyp werden ausschließlich Testdaten verarbeitet (Datenschutz). | Autorisierungstests je Endpunkt, npm audit, pip-audit, Image-Scan, Secret-Scan, Checkliste Datenschutz | --- |
| QZ-07 | Wartbarkeit | Linter und Typprüfung laufen ohne Fehler; jeder Merge auf main erfolgt nach Code-Review; Zeilenabdeckung der Backend-Unit-Tests ≥ 70 %; jeder API-Endpunkt besitzt mindestens einen automatisierten Test; Frontend und Backend sind getrennt bau- und testbar. | ESLint, svelte-check, Ruff, pytest-cov, Branch Protection, Endpunktliste gegen Testliste | --- |
| QZ-08 | Übertragbarkeit | Das Gesamtsystem startet aus leerem Zustand mit docker compose up anhand der Betriebsdokumentation; Kernfunktionen sind in aktuellen Versionen von Chrome, Firefox und Safari sowie auf Smartphone-Displaybreite nutzbar. | Deployment-Test auf sauberer Umgebung durch nicht beteiligte Person, Playwright mit mehreren Browser-Engines | --- |


### Qualität des Softwaresystems

### Qualität der Liefergegenstände