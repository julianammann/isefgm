# E2E-Testlauf der Ideenliste (#167, F-16)

Manueller Durchlauf der Seite `/ideas` im Browser, gesteuert über die Chrome DevTools (MCP). Jeder Schritt ist mit einem Screenshot belegt.

## Rahmen

| | |
| --- | --- |
| Datum | 04.11.2026, 09:25 bis 09:27 Uhr (MEZ) |
| Getesteter Stand | `cf6c9d2` auf `167-f-16-ideenliste-aus-verschenkten-geschenken-aller-konten` (PR #168), also `main` (`f918e36`) plus Ideenliste |
| Umgebung | lokal: Backend mit `fastapi dev`, Frontend mit `vite dev`, PostgreSQL 17.11 in einem eigenen Docker-Container nur für diesen Lauf, danach gelöscht. Die Registrierung war mit `REGISTRATION_ENABLED=true` geöffnet. |
| Browser | Google Chrome 156 (macOS), je ein isolierter Browser-Kontext ohne Cookies für Konto C und für den Zugriff ohne Anmeldung |
| Fenster | 1280 × 663 CSS-Pixel, Pixeldichte 2 (Screenshots 2560 × 1326 Pixel) |
| Testdaten | synthetisch, über die API angelegt, Adressen unter der reservierten Domain `example.org` (siehe unten) |

## Testdaten

| Konto | Personen | Verschenkt | Nur geplant |
| --- | --- | --- | --- |
| E2E Konto A | Tante Lena, Opa Jörg | „Kochbuch“, „Fotobuch für Lena“, „Kaffee für JÖRG“, „Lenas Kalender“ (alle an Tante Lena) | |
| E2E Konto B | Nachbarin | „ kochbuch “ (mit Leerzeichen am Rand), „Brettspiel“ | „Fahrrad“ |
| E2E Konto C | Bruder | „Armband“ | |

Konto C sieht sich die Seite an. Erwartet sind genau vier Titel: Armband, Brettspiel, Kochbuch und Lenas Kalender.

- „Fotobuch für Lena“ und „Kaffee für JÖRG“ fehlen, weil sie ein Wort aus dem Namen einer Person von Konto A enthalten. Opa Jörg hat nichts bekommen, zählt aber trotzdem.
- „ kochbuch “ ist ein Duplikat von „Kochbuch“.
- „Fahrrad“ wurde nicht verschenkt.
- „Lenas Kalender“ bleibt, weil „Lenas“ ein anderes Wort ist als „Lena“.

## Ablauf

| Nr. | Screenshot | Aktion | Ergebnis |
| --- | --- | --- | --- |
| 1 | `01-ideen-leer.png` | Als Konto C angemeldet, „Ideen“ in der Navigation angeklickt. Noch hat kein Konto etwas verschenkt. | „Noch keine verschenkten Geschenke.“ |
| 2 | `02-ideen-liste.png` | Daten von A, B und C angelegt, Seite neu geladen | Genau die vier erwarteten Titel, alphabetisch. Keine Fehler und keine Hydration-Warnungen in der Konsole. |
| 3 | `03-api-antwort-nur-titel.png` | `/api/v1/suggestions/titles` direkt im Browser geöffnet | `{"items":["Armband","Brettspiel","Kochbuch","Lenas Kalender"],"total":4,"limit":50,"offset":0}`. Keine IDs, Personen, Konten, Anlässe oder Daten. |
| 4 | `04-uebernommen-meldung.png` | „Übernehmen“ bei „Brettspiel“ | `POST /ideas?/adopt`, Meldung „Als Geschenkidee übernommen!“, die Seite bleibt `/ideas` |
| 5 | `05-geschenkidee-uebernommen.png` | „Geschenke“ in der Navigation | „Brettspiel“ ist eine eigene Idee von Konto C, Kategorie „Sonstiges“, noch keine Beschenkung |

Ohne Anmeldung leitet `/ideas` auf `/login?next=%2Fideas` um (303), und `GET /api/v1/suggestions/titles` antwortet mit 401.

Die einzige Meldung in der Konsole war eine 404 für `/favicon.ico`. Chrome hat das Icon beim direkten Aufruf der JSON-Antwort in Schritt 3 angefragt.

## Aufräumen

Der Datenbank-Container wurde nach dem Lauf gelöscht, mit ihm alle drei Konten und ihre Daten. Die gemeinsame Entwicklungsdatenbank wurde nicht verwendet.

## Abweichungen

- Der Lauf ist manuell und nur in Chrome. Die automatisierten Tests in Chromium, Firefox und WebKit aus #52 deckt er nicht ab.
