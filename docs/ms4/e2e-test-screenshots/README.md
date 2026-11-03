# E2E-Testlauf der Kernabläufe (#52, QZ-08)

Manueller Durchlauf der Kernabläufe im Browser, gesteuert über die Chrome DevTools (MCP). Jeder Schritt ist mit einem Screenshot belegt.

## Rahmen

| | |
| --- | --- |
| Datum | 03.11.2026, 22:48 bis 22:52 Uhr (MEZ) |
| Getesteter Stand | `91da04b` auf `feature/F-14-teilen-links-verwaltung-und-geteilte-ansicht-frontend` (PR #164), also `main` (`f918e36`) plus Teilen-Links (F-14) |
| Umgebung | lokal: Backend mit `fastapi dev`, Frontend mit `vite dev`, PostgreSQL 17.11 im Docker-Container. Die Registrierung war für den Lauf mit `REGISTRATION_ENABLED=true` geöffnet. |
| Browser | Google Chrome 156.0.8078.80 (macOS), je ein isolierter Browser-Kontext ohne Cookies für das Konto und für den Zugriff ohne Anmeldung |
| Fenster | 1280 × 663 CSS-Pixel, Pixeldichte 2 (Screenshots 2560 × 1326 Pixel) |
| Testdaten | synthetisch: Konto „E2E-Test“ (`e2e-test@example.org`, reservierte Domain, bekommt keine Mails), Person „Testperson E2E“, Idee „Kriminalroman“ |

## Ablauf

| Nr. | Screenshot | Aktion | Ergebnis |
| --- | --- | --- | --- |
| 1 | `01-registrieren-formular.png` | Registrierung: Anzeigename, E-Mail-Adresse und Passwort eingetragen | Formular ausgefüllt |
| 2 | `02-registriert-startseite.png` | „Konto anlegen“ abgeschickt | Konto angelegt und angemeldet, Startseite „Hallo E2E-Test“ |
| 3 | `03-person-anlegen-formular.png` | „Person hinzufügen“: Name, Geburtstag 12.05.1990, Beziehung, Notiz | Formular ausgefüllt |
| 4 | `04-person-angelegt.png` | „Anlegen“ | Meldung „Person angelegt!“, Person steht in der Liste |
| 5 | `05-idee-anlegen-formular.png` | „Geschenkidee hinzufügen“: Titel, Beschreibung, Kategorie Bücher, Preis 12,00 bis 18,00 EUR, mögliche Empfängerin Testperson E2E, Anlass Weihnachten | Formular ausgefüllt (der Titel liegt oberhalb des sichtbaren Bereichs) |
| 6 | `06-idee-angelegt.png` | „Anlegen“ | Meldung „Geschenkidee angelegt!“, Idee „für Testperson E2E“, noch keine Beschenkung |
| 7 | `07-beschenkung-anlegen-formular.png` | „+ Beschenkung“: Status Geplant, Empfängerin Testperson E2E, Anlass Weihnachten, Anlasstermin 24.12.2025 | Die Auswahl von Weihnachten belegt den Termin mit 24.12.2026 vor (F-11). Für den Test auf 24.12.2025 geändert, damit das Geschenk danach in der Vergangenheit liegt. |
| 8 | `08-beschenkung-geplant.png` | „Anlegen“ | Meldung „Beschenkung angelegt!“, Beschenkung mit Status „Geplant“ |
| 9 | `09-beschenkung-verschenkt-formular.png` | Beschenkung bearbeiten: Status Verschenkt, Verschenkdatum 24.12.2025 | Empfänger, Anlass und Anlasstermin werden Pflichtfelder, das Feld „Verschenkdatum“ erscheint |
| 10 | `10-beschenkung-verschenkt.png` | „Speichern“ | Meldung „Änderungen an der Beschenkung gespeichert!“, Status „Verschenkt“, verschenkt am 24.12.2025 |
| 11 | `11-person-vergangene-geschenke.png` | Personenseite geöffnet | „Vergangene Geschenke (1)“ mit dem Kriminalroman |
| 12 | `12-teilen-link-formular.png` | „Teilen“ auf der Personenseite, gültig bis 31.12.2026 | Person ist vorausgewählt, der Dialog sagt, was der Link zeigt und was privat bleibt |
| 13 | `13-teilen-link-erstellt.png` | „Link erstellen“ | Dialog „Link erstellt“ zeigt den Link einmalig zum Kopieren, „Geteilte Links (1)“ |
| 14 | `14-geteilte-ansicht-ohne-anmeldung.png` | Link in einem neuen Browser-Kontext ohne Cookies geöffnet | HTTP 200, „Geschenkideen von E2E-Test“, gültig bis 31.12.2026, Idee mit Kategorie, Preis und Beschreibung. Keine Navigation, keine Formulare, keine Buttons. Header `Referrer-Policy: no-referrer`, `X-Robots-Tag: noindex`, `Cache-Control: no-store`. |
| 15 | `15-teilen-link-schreibversuche-abgewiesen.png` | Schreib-Requests über den Teilen-Link ohne Anmeldung, Ergebnis als markierte Testausgabe über der Seite eingeblendet | Alle Schreibversuche mit 405 abgewiesen, Daten unverändert (Details unten) |
| 16 | `16-konto-loeschen-bestaetigung.png` | Konto-Seite, Bestätigung „Ich möchte mein Konto und alle Daten endgültig löschen.“ angehakt | Bereit zum Löschen |
| 17 | `17-konto-geloescht-login.png` | „Konto endgültig löschen“ | Weiterleitung auf „Anmelden“ |
| 18 | `18-anmeldung-geloeschtes-konto-abgewiesen.png` | Anmeldung mit dem gelöschten Konto | „E-Mail-Adresse oder Passwort ist falsch.“ |
| 19 | `19-teilen-link-nach-kontoloeschung-404.png` | Teilen-Link aus Schritt 13 erneut geöffnet | HTTP 404, „Dieser Link ist nicht gültig oder nicht mehr aktiv.“ |

## Schreibversuche über den Teilen-Link (Schritt 15)

Gesendet aus dem Browser-Kontext ohne Anmeldung. Der Token ist gekürzt. Als JSON-Body ging `{"title":"Manipuliert","person_ids":[]}` mit, beim Formular `title=Manipuliert`.

| Methode | Ziel | Antwort | `Allow` |
| --- | --- | --- | --- |
| PUT | `/api/v1/shared/sJkioF…` | 405 Method Not Allowed | GET |
| POST | `/api/v1/shared/sJkioF…` | 405 Method Not Allowed | GET |
| PATCH | `/api/v1/shared/sJkioF…` | 405 Method Not Allowed | GET |
| DELETE | `/api/v1/shared/sJkioF…` | 405 Method Not Allowed | GET |
| POST | `/shared/sJkioF…` (Seite, Formular) | 405 Method Not Allowed | GET |

Die API antwortete jeweils mit `{"type":"about:blank","title":"Method Not Allowed","status":405,"detail":"Method Not Allowed"}`. Die Seite `/shared/…` hat keine Formular-Aktionen, SvelteKit antwortete mit `{"type":"error","error":{"status":405,"message":"Method Not Allowed"}}`. Ein anschließendes `GET /api/v1/shared/sJkioF…` lieferte 200 mit unveränderten Daten (Testperson E2E: Kriminalroman).

## Aufräumen

Nach dem Lauf gibt es in der lokalen Datenbank weder das Konto `e2e-test@example.org` noch die Person „Testperson E2E“, und keine Idee und kein Teilen-Link ist ohne Konto zurückgeblieben. Der Link aus Screenshot 13 öffnet nichts mehr (Screenshot 19).

## Abweichungen von #52

- Der Lauf ist manuell und nur in Chrome. #52 sieht automatisierte Playwright-Tests in Chromium, Firefox und WebKit vor.
- Er läuft nicht automatisch auf `main` und vor Releases.
- Getestet wurde `main` plus PR #164, weil die Teilen-Links zum Zeitpunkt des Laufs noch nicht auf `main` waren.

## Beobachtung

Die geteilte Ansicht zeigt alle Ideen, die mit der Person verknüpft sind, auch eine bereits verschenkte (Screenshot 14). Die Personenseite zählt dieselbe Idee nicht mehr als offene Geschenkidee (Screenshot 11: „Geschenkideen (0)“).
