# Geschenke-Manager (isefgm)

Monorepo für den Geschenke-Manager: FastAPI-Backend, TypeScript-Frontend und Projektdokumentation.

## Struktur
```
backend/     FastAPI & SQLAlchemy 2.0 async & Alembic & Python 3.14 → backend/README.md
frontend/    TypeScript & Node 26 & pnpm                            → frontend/README.md
docs/        ER-Modell, Milestone-Dokumente, LaTeX-Quellen, Präsentationen
.github/     CI-Workflows (pfadgefiltert pro Komponente), Dependabot
compose.yaml Postgres, Migrationen, API für die lokale Entwicklung
mise.toml    Toolversionen und Tasks für das gesamte Projekt
lefthook.yml Git-Hooks (Lint, Format, Secret-Scan, Typecheck, Migrationsprüfung)
```

## Voraussetzungen
- [mise](https://mise.jdx.dev) installiert Python, Node, pnpm, uv, Lefthook und gitleaks in den gepinnten Versionen
- Docker (Desktop oder Engine) mit Compose

Kein lokales Postgres auf Port 5432 – falls eins läuft, stoppen oder den Port in `compose.yaml` ändern.
 
## Setup

```sh
git clone https://github.com/julianammann/isefgm.git && cd isefgm
mise trust && mise trust backend/mise.toml frontend/mise.toml
mise install                 # Toolchain
mise run setup               # uv sync, pnpm install, lefthook install
cp .env.example .env
mise run db                  # Postgres starten
mise -C backend run migrate  # Schema anlegen
mise -C backend run dev      # http://localhost:8000/docs
```

## Tasks

| Task (Root) | Beschreibung |
|---|---|
| `mise run setup` | Alle Dependencies und Git-Hooks installieren |
| `mise run db` | Postgres-Container starten |
| `mise run check` | Lint, Typecheck und Tests für Backend und Frontend |
| `mise run openapi` | OpenAPI-Schema exportieren und TypeScript-Typen generieren |
| `mise run docker` | Images bauen (uv-Version aus `mise.toml`) |

Komponenten-Tasks: `mise -C backend run <task>` bzw. `mise -C frontend run <task>` oder `mise run <task>` im jeweiligen Ordner. Übersicht mit `mise tasks`.

## Entwicklungsablauf

1. Feature-Branch von `main`, Namensschema `feature/<thema>`
2. Commits im [Conventional-Commits](https://www.conventionalcommits.org)-Stil: `feat(backend): …`, `fix(frontend): …`, `docs: …`
3. `pre-commit`-Hook formatiert und lintet automatisch, `pre-push` prüft Typen und Migrationen
4. Pull Request gegen `main`; CI muss grün seinDie Hooks überspringen bei Bedarf: `LEFTHOOK_EXCLUDE=alembic-check git push` (z. B. ohne laufende DB).

## CI

Workflows laufen nur für die geänderte Komponente:

| Workflow | Prüft |
|---|---|
| `backend.yml` | Ruff, Pyright (strict), Alembic-Migrationen gegen Postgres, pytest, pip-audit |
| `frontend.yml` | ESLint, tsc, Vitest, Build, Aktualität der generierten API-Typen |
| `docker.yml` | Image-Build und Push nach GHCR bei `main` und Tags `v*` |
| `gitleaks.yml` | Secret-Scan über die gesamte Historie |

## Docker

```sh
mise run docker
docker compose up -d
curl localhost:8000/api/v1/health/ready
```

`migrate` führt `alembic upgrade head` als Init-Container aus; `api` startet erst danach.

## Team
Anton, Jordan, Julian, Yin – Projekt im Rahmen des Moduls ISEF. Milestone-Dokumente unter `docs/`.