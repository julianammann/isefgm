# Screenshots für das Benutzerhandbuch (LG-05)

Automatisierter Durchlauf der Kernabläufe mit Playwright. Die Screenshots sind die Abbildungen in `../benutzerhandbuch.tex`. Sie ersetzen dort die Bilder aus `docs/ms4/e2e-test-screenshots/`, weil die Navigation inzwischen den Punkt „Ideen“ hat.

## Rahmen

| | |
| --- | --- |
| Datum | 06.11.2026 |
| Getesteter Stand | `ea8a375` auf `feature/benutzerhandbuch`. Die Oberfläche (`frontend/src`) ist identisch mit `main` (`fc28c35`). |
| Umgebung | lokal: Backend mit `uvicorn` (Port 8100), Frontend mit `vite dev` (Port 3100), lokale PostgreSQL. Für den Lauf waren `REGISTRATION_ENABLED=true` gesetzt und `API_URL` auf das Backend gerichtet. |
| Browser | Chromium 156.0.8078.4 über Playwright, je ein eigener Browser-Kontext für das Konto und für den Zugriff ohne Anmeldung, Browsersprache `--lang=de-DE` (sonst zeigen Datumsfelder das US-Format), Locale `de-DE`, Zeitzone `Europe/Berlin` |
| Fenster | 1280 × 663 CSS-Pixel, Pixeldichte 2 (Screenshots 2560 × 1326 Pixel), wie in `docs/ms4/e2e-test-screenshots/` |
| Testdaten | synthetisch: Konto „E2E-Test“ (`e2e-test@example.org`, reservierte Domain), Person „Testperson E2E“, Idee „Kriminalroman“ |

## Ablauf

| Nr. | Screenshot | Aktion | Ergebnis |
| --- | --- | --- | --- |
| 1 | `01-registrieren-formular.png` | Registrierung: Anzeigename, E-Mail-Adresse, Passwort | Formular ausgefüllt |
| 2 | `02-registriert-startseite.png` | „Konto anlegen“ | angemeldet, Startseite „Hallo E2E-Test“, Navigation mit „Ideen“ |
| 3 | `03-person-anlegen-formular.png` | „Person hinzufügen“: Name, Geburtstag 14.05.1990, Beziehung, Notiz | Formular ausgefüllt |
| 4 | `04-person-angelegt.png` | „Anlegen“ | Meldung „Person angelegt!“ |
| 5 | `05-idee-anlegen-formular.png` | „Geschenkidee hinzufügen“: Titel, Beschreibung, Bücher, 12,00 bis 18,00 EUR, Empfängerin, Weihnachten; Dialog nach unten gescrollt | Formular ausgefüllt |
| 6 | `06-idee-angelegt.png` | „Anlegen“ | Idee „für Testperson E2E“, noch keine Beschenkung |
| 7 | `07-beschenkung-anlegen-formular.png` | „+ Beschenkung“: Geplant, Empfängerin, Weihnachten | Anlasstermin mit 24.12.2026 vorbelegt (F-11), für den Ablauf auf 24.12.2025 geändert |
| 8 | `08-beschenkung-geplant.png` | „Anlegen“ | Meldung „Beschenkung angelegt!“, Status „Geplant“ |
| 9 | `09-beschenkung-verschenkt-formular.png` | Beschenkung bearbeiten: Verschenkt, Verschenkdatum 24.12.2025 | Feld „Verschenkdatum“ erscheint |
| 10 | `10-beschenkung-verschenkt.png` | „Speichern“ | Status „Verschenkt“, verschenkt am 24.12.2025 |
| 11 | `11-person-vergangene-geschenke.png` | Personenseite | „Vergangene Geschenke (1)“ |
| 12 | `12-teilen-link-formular.png` | „Teilen“, gültig bis 31.12.2026 | Person vorausgewählt |
| 13 | `13-teilen-link-erstellt.png` | „Link erstellen“ | Dialog „Link erstellt“ |
| 14 | `14-geteilte-ansicht-ohne-anmeldung.png` | Link im Kontext ohne Anmeldung | HTTP 200, geteilte Ansicht |
| 16 | `16-konto-loeschen-bestaetigung.png` | Konto-Seite, Bestätigung angehakt | bereit zum Löschen |
| 17 | `17-konto-geloescht-login.png` | „Konto endgültig löschen“ | Weiterleitung auf „Anmelden“ |
| 18 | `18-anmeldung-geloeschtes-konto-abgewiesen.png` | Anmeldung mit dem gelöschten Konto | „E-Mail-Adresse oder Passwort ist falsch.“ |
| 19 | `19-teilen-link-nach-kontoloeschung-404.png` | Link aus Schritt 13 erneut geöffnet | HTTP 404, „Dieser Link ist nicht gültig oder nicht mehr aktiv.“ |

Die Nummern folgen `docs/ms4/e2e-test-screenshots/`. Nummer 15 (Schreibversuche über den Teilen-Link) fehlt, weil sie für das Handbuch keine Rolle spielt; sie ist dort protokolliert.

Im Browser traten keine Seitenfehler auf.

## Aufräumen

Das Konto wurde im Ablauf selbst gelöscht (Schritt 17). Eine anschließende Anmeldung gegen das Entwicklungs-Backend antwortet mit 401.
