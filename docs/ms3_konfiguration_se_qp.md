# Konfiguration der Softwareentwicklung und Qualitätsplanung

## Konfiguration der Softwareentwicklung

## Konfiguration der Liefergegenstände

## Qualitätsplanung

### Qualitätsziele

Qualitätskriterien nach ISO/IEC 25010

| ID | Merkmal | Qualitätsziel | Prüfverfahren | Zeitpunkt / Verantwortlich |
| --- | --- | --- | --- | --- |
| QZ-01 | Funktionale Eignung | Alle als „Muss“ priorisierten Anforderungen sind umgesetzt und durch mindestens einen Testfall abgedeckt; 100 % der Muss-Testfälle sind bestanden. Berechnungen sind korrekt, z. B. enthält die Geburtstagsübersicht des Folgemonats genau die betroffenen Personen. Die Umwandlung einer Geschenkidee in ein Geschenk erfolgt in einem Schritt. | Rückverfolgbarkeitsmatrix Anforderung ↔ Testfall; Unit-, Integrations- und Systemtests | Je Sprint |
| QZ-02 | Leistungseffizienz | Die Listenansicht mit 200 Personen und 500 Geschenken wird in höchstens 2 Sekunden geladen (lokale Testumgebung). | Lasttest mit generierten Testdaten, Messung im Browser | --- |
| QZ-03 | Kompatibilität | Der Frontend-Client entspricht der OpenAPI-Spezifikation des Backends (typisierter Client, keine Typfehler); der HTML-Export ist valides HTML. | Typprüfung in CI, W3C-Validator | --- |
| QZ-04 | Benutzbarkeit | Eine Geschenkidee kann ohne Anleitung in höchstens 3 Interaktionen und unter 30 Sekunden erfasst werden; Löschvorgänge erfordern eine Bestätigung; ungültige Eingaben erzeugen verständliche Fehlermeldungen; Lighthouse-Accessibility-Wert ≥ 90. | Usability-Test mit 3 Testpersonen außerhalb des Teams, Testfälle mit ungültigen Eingaben, Lighthouse-Audit | --- |
| QZ-05 | Zuverlässigkeit | Geburtstagsbenachrichtigungen und Weihnachts-Statusmeldungen werden zum vorgesehenen Zeitpunkt vollständig und ohne Duplikate erzeugt; der Ausfall eines externen Dienstes (E-Mail-Versand, KI-Ideengenerierung) beeinträchtigt die Kernfunktionen nicht; Container starten nach Neustart automatisch. | Scheduler-Test mit simulierter Systemzeit, Integrationstest mit simuliertem Ausfall, Neustart-Test | --- |
| QZ-06 | Sicherheit | Nutzende können ausschließlich auf eigene Daten zugreifen; Passwörter werden nur gehasht gespeichert; geteilte Links sind nicht erratbar und widerrufbar; keine Schwachstellen mit Schweregrad kritisch oder hoch in Abhängigkeiten und Images; keine Secrets im Repository; im Prototyp werden ausschließlich Testdaten verarbeitet (Datenschutz). | Autorisierungstests je Endpunkt, npm audit, pip-audit, Image-Scan, Secret-Scan, Checkliste Datenschutz | --- |
| QZ-07 | Wartbarkeit | Linter und Typprüfung laufen ohne Fehler; jeder Merge auf main erfolgt nach Code-Review; Zeilenabdeckung der Backend-Unit-Tests ≥ 70 %; jeder API-Endpunkt besitzt mindestens einen automatisierten Test; Frontend und Backend sind getrennt bau- und testbar. | ESLint, svelte-check, Ruff, pytest-cov, Branch Protection, Endpunktliste gegen Testliste | --- |
| QZ-08 | Übertragbarkeit | Das Gesamtsystem startet aus leerem Zustand mit docker compose up anhand der Betriebsdokumentation; Kernfunktionen sind in aktuellen Versionen von Chrome, Firefox und Safari sowie auf Smartphone-Displaybreite nutzbar. | Deployment-Test auf sauberer Umgebung durch nicht beteiligte Person, Playwright mit mehreren Browser-Engines | --- |


### Qualität des Softwaresystems

### Qualität der Liefergegenstände