# Betriebsdokumentation Geschenke-Manager (isefgm)

Stand: 04.11.2026 · Liefergegenstand LG-08 · [Issue #64](https://github.com/julianammann/isefgm/issues/64)

Diese Anleitung beschreibt Installation, Konfiguration und Betrieb des Geschenke-Managers als Docker-Compose-Stack unter Windows (PowerShell), macOS (zsh oder Bash) und Linux (Bash). Alle Befehle laufen im Repository-Hauptverzeichnis, soweit nicht anders angegeben.

## 1. Benötigte Tools

Python, Node, uv und pnpm werden für den Containerbetrieb nicht auf dem Host gebraucht.

| Tool | Wofür | Offizielle Quelle |
| --- | --- | --- |
| Git | Repository klonen | https://git-scm.com/install/ |
| Docker Desktop (Windows, macOS) bzw. Docker Engine (Linux), jeweils mit Compose v2 | Container bauen und betreiben | Desktop: https://docs.docker.com/desktop/ · Engine: https://docs.docker.com/engine/install/ |
| curl (optional) | Health-Check unter macOS und Linux | https://curl.se/download.html |

Paketmanager: winget unter Windows (https://learn.microsoft.com/windows/package-manager/winget/), Homebrew unter macOS (https://brew.sh), apt unter Debian und Ubuntu.

**Windows (PowerShell, winget):**

```text
winget install --id Git.Git -e --source winget
winget install -e --id Docker.DockerDesktop
```

Docker Desktop danach starten. Standard ist das WSL-2-Backend mit Linux-Containern. Für den Health-Check reicht PowerShell, curl ist nicht nötig.

**macOS (Homebrew):**

```sh
brew install git
brew install --cask docker-desktop
```

Docker Desktop danach starten. curl ist auf macOS vorinstalliert.

**Linux (Debian/Ubuntu, apt):**

```sh
sudo apt update
sudo apt install git curl
```

Für Docker Engine zuerst das apt-Repository von Docker einrichten, wie unter https://docs.docker.com/engine/install/ubuntu/ bzw. https://docs.docker.com/engine/install/debian/ beschrieben. Danach:

```sh
sudo apt install docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
```

Andere Distributionen: https://docs.docker.com/engine/install/. Wer Docker ohne `sudo` nutzen will, richtet das nach https://docs.docker.com/engine/install/linux-postinstall/ ein.

**Prüfen (alle Plattformen):**

```text
git --version
docker version
docker compose version
```

`docker version` muss auch einen Server-Abschnitt zeigen. Fehlt er, Docker Desktop bzw. den Docker-Dienst starten.

Außerdem nötig: Internetzugang für Klonen und Image-Downloads sowie die freien Ports 3000 (Frontend), 8000 (API), 5432 (PostgreSQL), 8025 (Mailpit-Weboberfläche) und 1025 (Mailpit-SMTP).

## 2. Entwicklungsumgebung

Für die Entwicklung kommt mise dazu. Es installiert die in `mise.toml` festgelegten Versionen von Python, Node, pnpm, uv, Lefthook, gitleaks, Java (für den W3C-Validator in den Frontend-Tests) und Trivy und stellt die Projekt-Tasks bereit. Git und Docker aus Abschnitt 1 werden weiterhin gebraucht.

### 2.1 mise installieren

| Tool | Wofür | Offizielle Quelle |
| --- | --- | --- |
| mise | Toolversionen und Tasks | https://mise.jdx.dev/installing-mise.html |

**Windows (PowerShell, winget):**

```text
winget install jdx.mise
if (-not (Test-Path $PROFILE)) { New-Item -ItemType File -Path $PROFILE -Force | Out-Null }
Add-Content $PROFILE '(&mise activate pwsh) | Out-String | Invoke-Expression'
```

**macOS (Homebrew, zsh):**

```sh
brew install mise
echo 'eval "$(mise activate zsh)"' >> "${ZDOTDIR:-$HOME}/.zshrc"
```

**Linux (Debian 11+ / Ubuntu 22.04+, apt, Bash):**

```sh
sudo apt install -y extrepo
sudo extrepo enable mise
sudo apt update
sudo apt install -y mise
echo 'eval "$(mise activate bash)"' >> ~/.bashrc
```

Unter macOS mit Bash statt zsh die Bash-Zeile aus dem Linux-Block verwenden. Danach ein neues Terminal öffnen. Details zur Shell-Aktivierung: https://mise.jdx.dev/getting-started.html

Unter Windows laufen alle Tasks aus PowerShell. `.gitattributes` erzwingt LF-Zeilenenden, `core.autocrlf` spielt keine Rolle.

### 2.2 Projekt einrichten

```text
git clone https://github.com/julianammann/isefgm.git
cd isefgm
mise trust
mise trust backend/mise.toml frontend/mise.toml
mise install         # Toolchain aus mise.toml
mise run setup       # uv sync, pnpm install, lefthook install
```

Danach `.env` anlegen wie in Abschnitt 3.2. mise lädt `.env` automatisch für alle Tasks. Der Dev-Server liest daraus `DATABASE_URL` (Pflicht, ohne Standardwert). Der Wert muss auf die lokale Datenbank zeigen, zum Beispiel `postgresql+asyncpg://app:<POSTGRES_PASSWORD>@localhost:5432/app`.

Auf Port 5432 darf kein anderes PostgreSQL laufen.

### 2.3 Lokal starten

```text
mise run db                    # PostgreSQL im Container
mise -C backend run migrate    # Schema anlegen
mise -C backend run dev        # API mit Reload, http://localhost:8000/docs
mise -C frontend run dev       # Frontend, http://localhost:3000
```

Backend und Frontend laufen jeweils in einem eigenen Terminal. Das Frontend erwartet das Backend auf Port 8000. Läuft der Compose-Stack aus Abschnitt 3, sind die Ports 3000 und 8000 belegt. Dann vorher `docker compose stop` ausführen.

Den Scheduler bei Bedarf zusätzlich starten. Er schickt E-Mails an Mailpit (http://localhost:8025):

```text
docker compose up -d mailpit
mise -C backend run scheduler
```

### 2.4 Wichtige Tasks

| Task | Zweck |
| --- | --- |
| `mise run check` | Lint, Typecheck und Tests für Backend und Frontend |
| `mise -C backend run test` | Backend-Tests, braucht Docker (Testcontainers) |
| `mise -C backend run migration -- "<beschreibung>"` | Neue Alembic-Migration erzeugen, DB muss laufen |
| `mise -C backend run create-user -- --email <adresse> --display-name <name>` | Konto anlegen, fragt das Passwort ab |
| `mise -C backend run seed` | Testkonten aus Abschnitt 4.2 neu anlegen |
| `mise run openapi` | OpenAPI-Schema exportieren und TypeScript-Typen erzeugen |
| `mise run docs` | Doku aus dem Code nach `docs/generated/` erzeugen |
| `mise run apidocs:serve` | Code-Referenz bauen, Vorschau unter http://localhost:4173 |

Alle Tasks zeigt `mise tasks`.

### 2.5 Entwicklungsablauf

1. Branch von `main` anlegen. Name nach dem Issue als `<issue-nr>-<thema>`, alternativ `feature/<thema>` oder `fix/<thema>`.
2. Commits im Stil von [Conventional Commits](https://www.conventionalcommits.org) schreiben, zum Beispiel `feat(backend): ...`, `fix(frontend): ...`, `docs: ...`.
3. Lefthook prüft lokal. `pre-commit` formatiert und lintet die geänderten Dateien (Ruff, ESLint, Prettier), erzeugt bei API-Änderungen die OpenAPI-Typen neu und sucht mit gitleaks nach Secrets. `pre-push` prüft die Typen (Pyright, svelte-check) und mit `alembic check` die Migrationen, dafür muss die DB laufen. Ohne laufende DB den Check überspringen: `LEFTHOOK_EXCLUDE=alembic-check git push`.
4. Pull Request gegen `main` stellen. Die CI muss grün sein.

Die CI-Workflows laufen nur für die geänderte Komponente:

| Workflow | Prüft |
| --- | --- |
| `backend.yml` | Ruff, Pyright, Alembic-Migrationen, pytest mit mindestens 70 % Zeilenabdeckung, pip-audit |
| `frontend.yml` | Lint, Typecheck, Tests, Build und Aktualität der generierten API-Typen |
| `docker.yml` | Image-Build mit Trivy-Scan, Push nach GHCR bei `main` und Tags `v*` |
| `gitleaks.yml` | Secret-Scan über die gesamte Historie |
| `docs.yml` | Code-Referenz bauen und auf GitHub Pages veröffentlichen |

## 3. Installation

### 3.1 Repository klonen

```text
git clone https://github.com/julianammann/isefgm.git
cd isefgm
```

### 3.2 Konfiguration anlegen

Nur wenn noch keine `.env` existiert:

```text
Copy-Item .env.example .env    # Windows (PowerShell)
cp .env.example .env           # macOS / Linux
```

In `.env` mindestens `POSTGRES_PASSWORD` auf ein eigenes, langes Passwort aus Buchstaben und Zahlen setzen. Compose setzt es direkt in eine Datenbank-URL ein, Sonderzeichen müssten dort kodiert werden. Beispiel für den lokalen Betrieb:

```dotenv
POSTGRES_PASSWORD=HIER_EIN_LANGES_ZUFAELLIGES_PASSWORT_EINTRAGEN
POSTGRES_USER=app
POSTGRES_DB=app
APP_ENV=development
LOG_LEVEL=INFO
DEFAULT_TIMEZONE=Europe/Berlin
REGISTRATION_ENABLED=false
ORIGIN=http://localhost:3000
```

### 3.3 Container bauen und starten

```text
docker compose up --build -d
docker compose ps -a
```

Compose lädt automatisch `compose.yaml` und `compose.override.yaml`. Der erste Start dauert wegen Downloads und Builds länger. Die Dienste starten in der Reihenfolge PostgreSQL, Migrationen, API und Scheduler, Frontend. Der Service `migrate` endet nach der Schema-Aktualisierung mit Exit-Code 0 und läuft nicht dauerhaft.

### 3.4 Betriebsbereitschaft prüfen

```text
# Windows (PowerShell)
Invoke-RestMethod http://localhost:8000/api/v1/health/live
Invoke-RestMethod http://localhost:8000/api/v1/health/ready

# macOS / Linux
curl --fail --show-error http://localhost:8000/api/v1/health/live
curl --fail --show-error http://localhost:8000/api/v1/health/ready
```

Beide Aufrufe müssen erfolgreich sein. Der Readiness-Endpunkt prüft zusätzlich die Datenbankverbindung. Alternativ beide URLs im Browser öffnen.

| Dienst | Adresse |
| --- | --- |
| Anwendung | http://localhost:3000 |
| API-Dokumentation (Entwicklungsmodus) | http://localhost:8000/docs |
| Lokales E-Mail-Postfach (Mailpit) | http://localhost:8025 |

## 4. Konto und Testdaten

### 4.1 Erstes Konto

Die öffentliche Registrierung ist standardmäßig geschlossen. Ein Konto wird im API-Container angelegt:

```text
docker compose exec api python -m giftmanager.create_user --email betreiber@example.org --display-name Betreiber
```

Das Skript fragt das Passwort (8 bis 128 Zeichen) zweimal verdeckt ab und meldet bei Erfolg `Created account ...`. Danach unter http://localhost:3000 anmelden.

Eine gesonderte Admin-Rolle gibt es nicht, auch ein per Kommandozeile angelegtes Konto hat keine erweiterten Rechte. Die technische Administration erfolgt über den Zugriff auf Host und Container.

### 4.2 Testdaten (optional)

```text
docker compose exec api python -m giftmanager.seed
```

Das Skript fragt ein gemeinsames Passwort zweimal verdeckt ab und legt zwei Testkonten an:

| E-Mail-Adresse | Anzeigename |
| --- | --- |
| test1@example.org | Testkonto 1 |
| test2@example.org | Testkonto 2 |

Je Konto entstehen 100 Personen, 20 zusätzliche Anlässe, 1.000 Geschenkideen, 1.000 Beschenkungen und Aufgaben, dazu die drei Regelanlässe aus der Kontoanlage. Die tatsächlichen Anzahlen gibt das Skript aus. Alle Daten sind synthetisch.

**Ein erneuter Lauf ersetzt beide Testkonten samt ihren Daten.** Ein fest eingebautes Testpasswort gibt es nicht.

## 5. Konfiguration

| Einstellung | Bedeutung |
| --- | --- |
| `POSTGRES_PASSWORD` | Pflicht. Bei bestehendem Volume ändert ein neuer Wert in `.env` das Datenbankpasswort nicht. |
| `POSTGRES_USER`, `POSTGRES_DB` | Datenbankbenutzer und Datenbank, Standard jeweils `app`. |
| `REGISTRATION_ENABLED` | Standard `false`. `true` öffnet die Registrierung in API und Frontend. |
| `DEFAULT_TIMEZONE` | Standard `Europe/Berlin`, für die Kalenderauswertung im Scheduler. |
| `ORIGIN` | Öffentliche Adresse der App für Links in E-Mails, lokal `http://localhost:3000`. |
| `IMAGE_TAG` | Container-Tag, Standard `main`. Für reproduzierbaren Serverbetrieb einen freigegebenen, festen Stand verwenden. |
| `APP_ENV`, `LOG_LEVEL` | Lokal setzt der Override für API und Scheduler fest `development` und `DEBUG`. Werte aus `.env` ändern das nicht. |

Nicht jede Anwendungseinstellung wird aus `.env` in die Container weitergereicht. `DATABASE_URL` setzt Compose aus den `POSTGRES_*`-Werten zusammen, `UPLOADS_DIR` steht fest auf `/data/uploads`. Weitere Einstellungen müssen im jeweiligen Service unter `environment` eingetragen werden. Alle Anwendungseinstellungen stehen in der [generierten Konfigurationstabelle](https://julianammann.github.io/isefgm/reference/configuration.html).

Nach einer Änderung die Container neu erstellen. Ein `restart` übernimmt die neue Umgebung nicht.

```text
docker compose up -d
```

## 6. Laufender Betrieb

### Status und Logs

```text
docker compose ps -a
docker compose logs --tail 100 api frontend scheduler migrate db
docker compose logs -f api scheduler
```

`Strg+C` beendet die fortlaufende Anzeige, die Container laufen weiter. Der Scheduler läuft als genau eine Instanz und schickt lokal alle E-Mails an Mailpit (http://localhost:8025). Reale Postfächer erreicht er dabei nicht.

### Stoppen und starten

```text
docker compose stop      # anhalten
docker compose start     # wieder starten
docker compose down      # Container und Netzwerk entfernen, Daten bleiben
docker compose up -d     # neu erstellen und starten
```

`docker compose down -v` löscht zusätzlich Datenbank und Uploads. Für einen normalen Neustart nie verwenden.

### Daten und Sicherung

- `pgdata`: PostgreSQL-Daten
- `uploads`: hochgeladene Bilder (die Datenbank hält nur die Metadaten)

Eine vollständige Sicherung umfasst beide Volumes. Eine automatische Sicherung ist für den synthetischen Testbetrieb nicht vorgesehen. Für erhaltenswerte Daten müssen Sicherung und Wiederherstellung gesondert festgelegt und getestet werden.

### Aktualisierung

Vorher bei erhaltenswerten Daten eine geprüfte Sicherung anlegen und den bisherigen Commit- und Image-Stand notieren. Dann den freigegebenen Stand auschecken und neu bauen:

```text
docker compose up --build -d
docker compose ps -a
```

Anschließend die Prüfung aus Abschnitt 3.4 wiederholen und Anmeldung sowie einen bestehenden Datensatz kontrollieren. Schemaänderungen laufen über den Service `migrate`. Ein zurückgesetztes Image ist bei Schemaänderungen kein erprobtes Rollback.
