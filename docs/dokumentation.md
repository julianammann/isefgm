# Dokumentation aus dem Code

MS 4 (11.10.2026) verlangt acht Liefergegenstände. Vier davon entstehen zum größten Teil aus dem Code, wenn vier Regeln beim Schreiben eingehalten werden. Dieses Dokument legt die Regeln fest, zeigt sie an den vorhandenen Dateien und beschreibt, wie die Dokumente erzeugt werden. Es ist Teil des MS-3-Abschnitts „Konfiguration der Liefergegenstände“.

## Was woher kommt

| Liefergegenstand MS 4 | Quelle | Erzeugt durch | Anteil aus Code |
|---|---|---|---|
| Technische Doku: Schnittstellen | `summary`/`description` an Endpoints, `Field(description=)` in Schemas, `OPENAPI_TAGS` | `mise run docs` → `docs/generated/api.md`; Details in `frontend/openapi.json` und `/docs` | fast vollständig |
| Technische Doku: Datenbank | `comment=` an Tabellen und Spalten | `mise run docs` → `docs/generated/database.md`; Beziehungen von Hand in `docs/datenmodell.md` | weitgehend |
| Technische Doku: Architektur, Komponenten | Backend- und Frontend-README, Modul-Docstrings | von Hand, Entwurf darf generiert werden (siehe unten) | teilweise |
| Technische Doku: Code-Referenz | Docstrings (Python), JSDoc (TypeScript), Typannotationen | `mise run apidocs` → `apidocs/` (VitePress-Seite aus Sphinx und TypeDoc), veröffentlicht auf GitHub Pages | vollständig |
| Betriebsdoku: Konfiguration | `Field(description=)` in `Settings` | `mise run docs` → `docs/generated/configuration.md` | vollständig |
| Betriebsdoku: Installation, Admin-Account | `compose*.yaml`, Deployment-Notizen (außerhalb des Repos), Seed-Skript | von Hand | teilweise |
| Testabschlussbericht | `@pytest.mark.requirement`, pytest, pytest-cov, Vitest, Playwright | `mise run test` → `docs/generated/traceability.md`, Coverage-Ausgabe, CI-Logs | vollständig |
| Fachliche Doku: Geschäftsregeln | Docstrings der Services, `DomainError`-Texte, fachlich benannte Tests | von Hand, Entwurf darf generiert werden | teilweise |
| Fachliche Doku: Prozesse, Konzepte | – | von Hand (Mermaid-Sequenzdiagramme, Glossar) | kaum |
| Benutzerhandbuch | Playwright-Screenshots | Text von Hand, Screenshots aus E2E-Tests | kaum |

## Die vier Regeln

Sie kosten beim Schreiben Sekunden und werden nicht nachträglich ergänzt. Ein Endpoint, eine Tabelle oder ein Test ohne diese Angaben ist nicht fertig (Teil der Definition of Done).

**1. Jede Tabelle und jede Spalte hat ein `comment`.** Alembic schreibt es nach PostgreSQL (`\d+ user_account` zeigt es), der Generator rendert es. In der Migration steht derselbe Text, sonst meldet `alembic check` eine Abweichung. Vorlage: `backend/src/giftmanager/models/user.py`.

```python
email: Mapped[str] = mapped_column(
    String(320),
    unique=True,
    comment="Login name. Stored lowercased and unique.",
)
```

**2. Jeder Endpoint hat `summary` und `description`, jedes Schema-Feld eine `description` und ein `examples`.** `summary` ist eine Zeile und wird zur Spalte „Purpose“, `description` erklärt das Verhalten, das ein Aufrufer wissen muss: Nebenwirkungen, Fehlerfälle, Idempotenz. Jeder Router-Tag hat einen Eintrag in `OPENAPI_TAGS` (`main.py`), der zur Kapiteleinleitung wird. Vorlage: `api/v1/auth.py`, `schemas/auth.py`.

```python
@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="authLogout",
    summary="Log out",
    description="Revokes the session on the server and clears the cookie. "
    "Idempotent: also works without a cookie or with one that is no longer valid.",
)
```

**3. Jeder Test nennt die Anforderungen, die er nachweist.** IDs aus MS 1 (`F-01` bis `F-19`, `Q-01` bis `Q-09`). `--strict-markers` lehnt Tippfehler im Markernamen ab. Tests ohne Marker landen in der Matrix unter „Tests without a requirement“ und werden im Review hinterfragt. Vorlage: `tests/test_auth.py`.

```python
@pytest.mark.requirement("F-01", "Q-03")
async def test_logout_revokes_the_session(client: AsyncClient, session: AsyncSession) -> None:
```

Dasselbe gilt für `Settings`: jedes Feld hat `Field(default=…, description=…)`; das ist die Konfigurationstabelle der Betriebsdoku.

**4. Jedes öffentliche Modul, jede Klasse und jede Funktion hat einen Docstring bzw. JSDoc.** Daraus entsteht die Code-Referenz, vergleichbar mit YARD bei Rails. Im Backend Google-Stil (`Args:`, `Returns:`, `Raises:` nur, wenn sie etwas sagen, das die Signatur nicht sagt); Ruff (`D1`) meldet fehlende Docstrings, Tests und Migrationen sind ausgenommen. Im Frontend beginnt jede Datei unter `src/lib` und `src/routes` mit einem `@module`-Kommentar, jeder Export hat JSDoc; TypeDoc bricht bei fehlender Doku ab (`typedoc.json`, `treatWarningsAsErrors`). Vorlagen: `backend/src/giftmanager/services/auth.py`, `frontend/src/routes/(auth)/login/+page.server.ts`.

```python
async def authenticate(session: AsyncSession, *, email: str, password: str) -> User | None:
    """Return the active user for the credentials, or None.

    Takes the same time for an unknown address as for a wrong password.
    """
```

## Sprache

Alles, was im Code steht, ist Englisch: Code, Kommentare, Docstrings, JSDoc und auch die Texte in `comment=`, `summary=`, `description=`, `examples=` sowie die Klassen-Docstrings der Pydantic-Schemas. Damit sind die daraus erzeugten Dokumente in `docs/generated/` ebenfalls Englisch.

Deutsch bleiben die von Hand geschriebenen Dokumente (READMEs, dieses Dokument, `docs/datenmodell.md`, die Milestone-Dokumente) und alle Texte, die Nutzer in der Oberfläche sehen.

## Erzeugen

```sh
mise run docs        # Backend: API, Datenbank, Konfiguration; danach voller Testlauf für die Matrix
mise run apidocs     # Code-Referenz als VitePress-Seite nach apidocs/ (Sphinx + TypeDoc)
mise run apidocs:serve   # dasselbe, danach Vorschau unter http://localhost:4173
```

| Datei in `docs/generated/` | Quelle | Erzeugt von |
|---|---|---|
| `api.md` | `app.openapi()` | `giftmanager/export_docs.py` |
| `database.md` | `Base.metadata` (Tabellen, Spalten, Typen, Kommentare, PK/FK/Index) | `giftmanager/export_docs.py` |
| `configuration.md` | `Settings.model_fields` | `giftmanager/export_docs.py` |
| `traceability.md` | Marker und Ergebnis jedes Tests | `tests/conftest.py` bei jedem pytest-Lauf |

Die Dateien werden committet, damit sie ohne Toolchain lesbar sind und Änderungen im PR-Diff sichtbar werden. Sie werden nie von Hand bearbeitet; die erste Zeile sagt das. Ein Teillauf (`pytest -k …`) überschreibt die Matrix mit einem Teilstand, deshalb vor dem Commit einmal vollständig `mise run test` ausführen. Für den Testabschlussbericht kommen die Coverage-Zeile aus `pytest-cov` und die CI-Logs des Release-Commits dazu.

Der Generator braucht keine Datenbank. Neue Modelle müssen in `models/__init__.py` importiert sein, sonst sieht er sie nicht (dieselbe Regel wie für Alembic).

### Code-Referenz

| Teil | Werkzeug | Quelle | Markdown nach |
|---|---|---|---|
| Backend | [Sphinx](https://www.sphinx-doc.org) (autodoc, napoleon) + sphinx-markdown-builder, `backend/docs/build.py` | Docstrings und Typannotationen aus `giftmanager` | `docs/site/backend/` |
| Frontend | [TypeDoc](https://typedoc.org) + typedoc-plugin-markdown, typedoc-vitepress-theme | JSDoc und Typen aus `src/lib`, `src/routes`, `hooks.server.ts` | `docs/site/frontend/` |
| Referenz | – | `docs/generated/*.md`, per `<!--@include-->` eingebunden | `docs/site/reference/` |

[VitePress](https://vitepress.dev) (`docs/site/`) baut daraus eine Seite mit Suche und Sidebar nach `apidocs/`. Die generierten Markdown-Seiten und `apidocs/` werden nicht committet. `.github/workflows/docs.yml` baut die Referenz bei jedem Pull Request (fehlende Frontend-Doku lässt den Lauf scheitern) und veröffentlicht sie bei jedem Push auf `main` auf GitHub Pages; der Link kommt ins Redmine-Ticket. Vorschau lokal: `mise run apidocs:serve`.

Nicht abgedeckt sind `.svelte`-Dateien: TypeDoc liest nur TypeScript. Logik gehört deshalb in `.ts`-Dateien (`load`, Actions, `$lib`), Komponenten bleiben schlank.

## Was von Hand geschrieben wird

Architekturüberblick, Prozessbeschreibungen, Glossar und Benutzerhandbuch lassen sich nicht aus dem Code ableiten. Für sie gilt:

- Ein Entwurf darf mit einem Sprachmodell aus Code und Tests erzeugt werden. Vor der Abgabe liest eine Person, die den Teil nicht geschrieben hat, den Text gegen den Code und zeichnet das im PR ab. Das ist das Prüfverfahren für „Qualität der Liefergegenstände“ in MS 3 und deckt Q-09 ab.
- Zahlen (Testanzahl, Coverage, Antwortzeiten aus Q-05) kommen ausschließlich aus echten Läufen, nie aus generiertem Text.
- Screenshots für das Benutzerhandbuch legen die Playwright-Flows an definierten Stellen ab (`page.screenshot({ path: "docs/handbuch/<flow>-<schritt>.png" })`), damit sie bei UI-Änderungen mitlaufen.
- Wie KI-Einsatz bei den MS-4-Dokumenten zu deklarieren ist, wird vor MS 3 mit dem Tutor geklärt und im MS-3-Dokument festgehalten.

## Bewusst nicht

- Nur `D1` aus pydocstyle (Docstring vorhanden), keine Stilregeln `D2`–`D4`: sie erzeugen Rauschen, ohne die Referenz besser zu machen. Private Funktionen (`_name`) brauchen keinen Docstring.
- Die handgeschriebenen deutschen Dokumente (READMEs, dieses Dokument, `docs/datenmodell.md`) stehen nicht auf der Doku-Seite; sie ist nur die Code-Referenz plus die daraus generierten Dokumente.
- Kein CI-Schritt, der `docs/generated/` auf Aktualität prüft. Der `openapi.json`-Diff in `backend.yml` fängt den wichtigsten Fall bereits. Nachrüsten, falls die Dateien in PRs regelmäßig veralten.
