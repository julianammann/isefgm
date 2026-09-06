# Projektvision

Der **Geschenke-Manager** wird als datenschutzorientierte, browserbasierte Webanwendung konzipiert und prototypisch umgesetzt. Die Anwendung unterstützt Nutzer:innen dabei, Personen, Anlässe, Geschenkideen, bereits verschenkte Geschenke und noch offene Aufgaben an einer zentralen Stelle zu verwalten. Damit sollen vergessene Anlässe, doppelte Geschenke und kurzfristiger Beschaffungsstress vermieden werden.

Personen, Anlässe und Geschenkideen/Geschenke werden unabhängig voneinander angelegt und bei Bedarf flexibel verknüpft. Eine Idee kann dadurch sofort erfasst werden, auch wenn Empfänger:in oder Anlass noch nicht feststehen. Umgekehrt kann ein Anlass geplant werden, bevor Personen oder Geschenke ausgewählt wurden.

Automatische Benachrichtigungen weisen auf bevorstehende Anlässe und noch nicht besorgte Geschenke hin. Widerrufbare Freigabelinks ermöglichen das kontrollierte Teilen ausgewählter Ideen. Weitere Vorschläge werden aus anonymisierten und aggregierten Merkmalen tatsächlich verschenkter Geschenke abgeleitet. Personenbezogene Daten anderer Konten bleiben dabei getrennt und werden nicht offengelegt.

# Vorstellung des Teams

| Teammitglied | Foto | Kurzprofil | Skills |
| --- | --- | --- | --- |
| **Yin Yin Wu-Hanke** | ![Yin](./images/team/yin.jpg) | Detection Engineer | Frontendentwicklung, Security |
| **Julian Ammann** | ![Julian](./images/team/julian.jpg) | Senior Full Stack Developer | Frontend- & Backendentwicklung, DevOps, Systemarchitektur |
| **Anton Hirsch** | ![Anton](./images/team/Anton.jpg) | im Bachelorstudiengang Informatik | Grundlagen in Python, Java, C++, SQL sowie KI-gestützter Recherche und Problemlösung |
| **Kevin Jordan Taghu** | ![Jordan](./images/team/jordan.PNG) | Data Analyst | Frontendentwicklung, Datenmodellierung, Reporting, Datenvisualisierung, Datenbereinigung |

# Anforderungen (auf grober Ebene)

Die Anforderungen werden in MS 1 bewusst auf grober Ebene beschrieben. Detaillierte Akzeptanzkriterien, Testfälle und die endgültige technische Umsetzung werden in MS 3 festgelegt. **MUSS** bezeichnet den vorgesehenen Kernumfang des Prototyps; **SOLL** wird umgesetzt, wenn dadurch der Pflichtumfang und dessen Qualität nicht gefährdet werden.

## Funktionale Anforderungen

| ID | Priorität | Anforderung |
| --- | --- | --- |
| F-01 | MUSS | Nutzer:innen können sich registrieren, anmelden und abmelden. Alle fachlichen Daten gehören genau einem Konto. |
| F-02 | MUSS | Personen können mit Name, Geburtstag, Beziehung, Notizen und Erstellzeitpunkt angelegt, angezeigt, geändert und gelöscht werden. |
| F-03 | MUSS | Geburtstag und Weihnachten stehen als feste Anlasstypen zur Verfügung; eigene einmalige und wiederkehrende Anlässe können angelegt werden. |
| F-04 | MUSS | Personen, Anlässe und Geschenkideen/Geschenke können unabhängig angelegt und anschließend flexibel in n:m-Beziehungen verknüpft oder wieder getrennt werden. |
| F-05 | MUSS | Eine Geschenkidee enthält mindestens Titel, Beschreibung, Status, Preisrahmen und Erstellzeitpunkt sowie optional ein Verschenkdatum. |
| F-06 | MUSS | Geschenkideen durchlaufen die Status **Idee**, **Geplant**, **Besorgt** und **Verschenkt**. Beim Übergang zu **Verschenkt** werden Anlass und Verschenkdatum dokumentiert. |
| F-07 | MUSS | Zu einer Geschenkidee können Links, Bilder beziehungsweise Anhänge und beschriftete Notizen gespeichert werden. |
| F-08 | MUSS | Zu einer Geschenkidee können Aufgaben mit den Status **Offen**, **In Bearbeitung**, **Erledigt** und **Verworfen** verwaltet werden. |
| F-09 | MUSS | Eine Personenansicht zeigt gleichzeitig vergangene Geschenke, offene Geschenkideen, Aufgaben und zugehörige Anlässe. |
| F-10 | MUSS | Das System erstellt Benachrichtigungen zu Geburtstagen im folgenden Monat und berücksichtigt bereits bekannte Geschenkideen. |
| F-11 | MUSS | Sechs Wochen vor Weihnachten beginnt eine regelmäßige Statusübersicht über geplante Empfänger:innen und den Beschaffungsstand. |
| F-12 | MUSS | Etwa zwei Wochen vor einem Anlass wird erinnert, wenn noch kein zugeordnetes Geschenk den Status **Besorgt** oder **Verschenkt** besitzt. |
| F-13 | MUSS | Planung, Versuch und Ergebnis eines Benachrichtigungsversands werden gespeichert; dieselbe Benachrichtigung darf nicht doppelt versendet werden. |
| F-14 | MUSS | Ideen ausgewählter Personen können über einen nicht erratbaren, optional ablaufenden und jederzeit deaktivierbaren Nur-Lese-Link geteilt werden. |
| F-15 | MUSS | Die vollständige eigene Liste kann als HTML-Ansicht beziehungsweise HTML-Export ausgegeben werden. |
| F-16 | MUSS | Das System erzeugt aus anonymisierten und aggregierten Merkmalen früherer Geschenke neue Vorschläge, schließt vorhandene und bereits verschenkte Ideen der Zielperson aus und ermöglicht die Übernahme oder Verwerfung. |
| F-17 | MUSS | Nutzer:innen können das eigene Konto einschließlich aller zugehörigen Daten vollständig löschen. |
| F-18 | SOLL | Ein Nutzerprofil verwaltet Zeitzone, Benachrichtigungseinstellungen und Einstellungen zur Barrierefreiheit, beispielsweise geeignete Farbschemata. |
| F-19 | SOLL | Der Turnus bestimmter Erinnerungen kann innerhalb vorgegebener Grenzen angepasst werden. |

## Qualitätsanforderungen

| ID | Qualitätsziel | Konkretisierung für das Projekt |
| --- | --- | --- |
| Q-01 | Mandantentrennung | Kein Datensatz eines fremden Kontos darf gelesen oder verändert werden. |
| Q-02 | Benachrichtigungszuverlässigkeit | Ein mehrfach ausgeführter Zeitplaner erzeugt für denselben Nutzer, dasselbe Ereignis und dasselbe Intervall keine zweite Nachricht. |
| Q-03 | Sicherheit | Passwörter werden mit einem etablierten Hashverfahren gespeichert. Die Anwendung nutzt HTTPS, sichere Sitzungen, serverseitige Autorisierung und nicht erratbare Freigabetokens. |
| Q-04 | Datenschutz | Für Tests werden synthetische Daten verwendet. Namen, E-Mail-Adressen, Freitextnotizen, URLs und Anhänge werden nicht kontenübergreifend für Vorschläge genutzt. |
| Q-05 | Leistung | Listen sollen bei einem Testbestand von 100 Personen und 1.000 Geschenkdatensätzen im Regelfall innerhalb von zwei Sekunden angezeigt werden. |
| Q-06 | Wartbarkeit | Das relationale Datenmodell wird mindestens bis zur dritten Normalform strukturiert. Code wird gelintet, getestet und vor der Zusammenführung geprüft. |
| Q-07 | Barrierearmut | Wesentliche Abläufe sind per Tastatur bedienbar; Zustände werden nicht ausschließlich über Farben vermittelt. |
| Q-08 | Zeitkorrektheit | Technische Zeitpunkte werden in UTC gespeichert. Geburtstage und andere reine Kalenderdaten werden ohne Uhrzeit gespeichert, damit sich der Kalendertag durch eine Zeitzone nicht verschiebt. |
| Q-09 | Nachvollziehbarkeit | Anforderungen, Arbeitspakete, Änderungen, Testfälle und Liefergegenstände werden über eindeutige Bezeichnungen miteinander verbunden. |

## Randbedingungen

### Technische Randbedingungen

- Umsetzung als browserbasierte Webanwendung mit Benutzeroberfläche, Backend/API und relationaler Datenbank.
- Der Tutor muss das System ohne lokale Installation über einen Link testen können.
- Die verbindliche Wahl von Programmiersprachen, Frameworks, Hosting und E-Mail-Dienst erfolgt in MS 3 nach einem kurzen technischen Probelauf.
- Bildanhänge werden geschützt gespeichert; die Datenbank enthält nur Metadaten und die Speicherreferenz.
- Geheimnisse, Passwörter und echte private Testdaten dürfen nicht im Git-Repository gespeichert werden.

### Organisatorische Randbedingungen

- Projektzeitraum: 20.08.2026 bis spätestens Ende Oktober 2026.
- Redmine wird zur formalen Bereitstellung der Meilensteine und zur Entgegennahme des Tutorfeedbacks verwendet. Bei einer Abgabe wird das zugehörige Ticket auf **Feedback** gesetzt und dem Tutor zugewiesen.
- Interne Besprechungen und ausführlichere Abstimmungen erfolgen über Microsoft Teams.
- Die Signal-Gruppe dient kurzfristigen Abstimmungen und wichtigen projektbezogenen Mitteilungen.
- Quellcode und technische Dokumentation werden in einem privaten Git-Repository versioniert.
- Spätestens vor Beginn der Implementierung wird der Hauptbranch geschützt. Änderungen sollen anschließend in eigenen Branches bearbeitet, durch ein weiteres Teammitglied geprüft und über Pull Requests zusammengeführt werden.
- Features und Fehlerkorrekturen werden in eigenen Branches bearbeitet und über Pull Requests in den geschützten Hauptbranch übernommen.
- Architektur-, Datenschutz-, Umfangs- und Terminentscheidungen werden schriftlich in der Projektdokumentation festgehalten.

### Konventionen

- Architektur und Datenmodell werden als versionierte Diagramme und Beschreibungen dokumentiert.
- Quellcode wird automatisch formatiert beziehungsweise gelintet.
- Unit-, Integrations-, Berechtigungs- und E2E-Tests sichern den Prototyp ab.
- Commit-Nachrichten sollen einem einheitlichen, kurzen Schema folgen; Conventional Commits können hierfür verwendet werden.

# Lösungsansatz

## Fachlicher Ansatz

Geschenkidee und Geschenk werden als ein gemeinsames Objekt **Geschenk/Idee** modelliert. Der Status bildet den Lebenszyklus von der ersten Idee bis zum tatsächlich verschenkten Geschenk ab. Dadurch muss beim „Umwandeln“ kein zweiter Datensatz erzeugt oder kopiert werden.

Personen, Anlässe und Geschenk/ Idee werden getrennt gespeichert. Direkte Fremdschlüssel auf genau eine Person oder genau einen Anlass werden für diese Beziehungen vermieden. Stattdessen ermöglichen Zuordnungstabellen flexible Verknüpfungen. Dadurch können unter anderem folgende Situationen abgebildet werden:

- eine Idee ohne bereits bekannte Person oder Anlass,
- ein gemeinsames Geschenk für mehrere Personen,
- eine Idee für mehrere mögliche Anlässe,
- ein Anlass mit mehreren geplanten Empfänger:innen,
- ein Anlass, für den noch kein Geschenk ausgewählt wurde.


## Vorgesehenes Zielmodell

| Entität / Beziehung | Wesentliche Inhalte |
| --- | --- |
| Nutzer | ID, E-Mail, Passwort-Hash, Anzeigename, Kontostatus, erstellt am |
| Nutzerprofil | Nutzer-ID, Zeitzone, Farbschema, Barrierefreiheits- und Benachrichtigungseinstellungen |
| Person | ID, Besitzer-Nutzer-ID, Name, Geburtstag, Beziehung, Notizen, erstellt am |
| Anlasstyp | ID, Besitzer-Nutzer-ID oder global, Name, Standardwiederholung |
| Anlass | ID, Besitzer-Nutzer-ID, Anlasstyp-ID, Name, Kalenderdatum, Wiederholungsregel |
| Geschenk/Idee | ID, Besitzer-Nutzer-ID, Titel, Beschreibung, Status, Preis von/bis, Währung, verschenkt am, erstellt am |
| Person–Anlass | flexible Zuordnung von Personen und Anlässen |
| Geschenk–Person | flexible Zuordnung von Geschenken/Ideen und Personen |
| Geschenk–Anlass | flexible Zuordnung von Geschenken/Ideen und Anlässen |
| Anhang | ID, Geschenk-ID, Art, Speicherreferenz/URL, Beschriftung |
| Aufgabe | ID, Geschenk-ID, Titel, Status, optional Fälligkeit |
| Teilen-Link | ID, Besitzer-Nutzer-ID, Token-Hash, aktiv, läuft ab, erstellt am |
| Teilen-Link–Person | explizit freigegebene Personen |
| Ideen-Vorschlag | ID, Besitzer-Nutzer-ID, Zielperson-ID, Titel, Begründung, Status, erstellt am |
| Benachrichtigung | ID, Besitzer-Nutzer-ID, Typ, Bezug, geplant für, Status, gesendet am, Fehler und Deduplizierungsschlüssel |

Bei jeder Beziehung wird serverseitig geprüft, dass alle beteiligten Datensätze demselben Nutzerkonto gehören.

## Benachrichtigungs- und Vorschlagsansatz

Ein regelmäßig ausgeführter Prozess ermittelt anstehende Ereignisse. Reine Kalenderdaten werden anhand der Profilzeitzone ausgewertet; der konkrete Versandzeitpunkt wird in UTC gespeichert. Vor dem Versand wird aus Nutzer, Ereignis, Ereignisjahr, Nachrichtentyp und Erinnerungsintervall ein eindeutiger Schlüssel gebildet. Dieser verhindert einen zweiten Versand derselben Nachricht.

Vorschläge verwenden nur minimierte Merkmale wie allgemeine Geschenkekategorie, Preisband, grobe Altersgruppe und Anlassart. Namen, Kontaktdaten, Notizen, Links und Anhänge werden ausgeschlossen. Bereits vorhandene oder verschenkte Geschenke der Zielperson werden vor der Anzeige herausgefiltert. Reichen reale Projektdaten für ausreichend große anonyme Gruppen nicht aus, wird die Funktion mit synthetischen Seed-Daten demonstriert.

# Annahmen und Beschränkungen

## Annahmen

- Das Thema und die Teamzusammensetzung sind durch den Tutor bestätigt oder werden vor Projektfortsetzung bestätigt.
- Alle vier Teammitglieder stellen bis Ende Oktober regelmäßig Zeit bereit und melden Abwesenheiten frühzeitig.
- Entwicklung, Tests und Präsentation verwenden ausschließlich synthetische oder ausdrücklich freigegebene Daten.
- Ein kontrollierter E-Mail-Testkanal und eine vom Tutor erreichbare Demo-Umgebung können bereitgestellt werden.
- Der Pflichtumfang wird als bewusst einfacher, aber durchgängiger Prototyp umgesetzt.

## Beschränkungen und Nicht-Ziele

- Es wird keine native Smartphone-App und keine Offline-Synchronisation entwickelt.
- Kalender-, Kontakt-, Händler-, Preisvergleichs- und Zahlungsintegrationen sind nicht Teil des MVP.
- Freigabelinks ermöglichen nur lesenden Zugriff; gemeinsames Bearbeiten ist nicht vorgesehen.
- Für Bildanhänge gelten festgelegte Dateitypen und Größenbeschränkungen.
- Das Vorschlagsverfahren bleibt für den Prototyp nachvollziehbar und verwendet keine personenbezogenen Freitexte.
- Die technische Detailkonfiguration und die vollständige Qualitätsplanung werden entsprechend der Aufgabenstellung erst mit MS 3 verbindlich festgelegt.

# Meilensteinplan (aktualisierte Version auf Basis von MS 0)

Der in MS 0 erstellte Meilensteinplan wurde anhand des aktuellen Projektstands überprüft und um interne Entwicklungs-, Review- und Reservezeiten konkretisiert. Die Meilensteine MS 0 bis MS 6 bilden weiterhin die verbindlichen Übergabepunkte. Zwischen den Meilensteinen werden die bekannten Arbeitspakete des Projektstrukturplans bearbeitet.

| Termin | Ergebnis |
| --- | --- |
| 20.08.2026 | MS 0: Meilensteinplan |
| 03.09.2026 | MS 1: Projektkonfiguration |
| 10.09.2026 | MS 2: Projektvideo |
| 17.09.2026 | MS 3: Konfiguration der Softwareentwicklung und Qualitätsplanung |
| 01.10.2026 | Abschluss der ersten Entwicklungsiteration |
| 08.10.2026 | Abschluss der zweiten Entwicklungsiteration |
| 15.10.2026 | MS 4: Softwaresystem und Dokumentation |
| 22.10.2026 | MS 5: Ergebnispräsentation |
| 29.10.2026 | MS 6: Projektbericht |
| 30.–31.10.2026 | Notfallreserve für unvorhergesehene Korrekturen |

Die letzten zwei Tage vor jedem Meilenstein werden grundsätzlich für Review, Korrektur, Export und Bereitstellung reserviert. Absehbare Terminabweichungen werden unmittelbar in der Signal-Gruppe mitgeteilt und im nächsten Teams-Termin gemeinsam bewertet.

# Liste von Liefergegenständen inkl. Zuordnung zu Meilenstein

| Meilenstein | Liefergegenstand | Bereitstellung und Vorgabe |
| --- | --- | --- |
| MS 0 | Meilensteinplan | PDF oder Bild in Redmine |
| MS 1 | Projektkonfiguration | PDF in Redmine |
| MS 2 | Projektvideo | Video oder Link in Redmine; maximal fünf Minuten |
| MS 3 | Konfiguration der Softwareentwicklung und Qualitätsplanung | PDF in Redmine |
| MS 4 | Benutzerhandbuch | in Redmine |
| MS 4 | fachliche Dokumentation - Prozesse, fachliche Konzepte, Geschäftsregeln | in Redmine |
| MS 4 | technische Dokumentation - Architektur, Komponenten, Schnittstellen, Datenbank | in Redmine |
| MS 4 | Betriebsdokumentation - Installation, Konfigurationen, Admin-Account | in Redmine |
| MS 4 | Testabschlussbericht inkl. Testfälle und Testprotokolle| in Redmine |
| MS 4 | Programmcode bzw. Link zum Repository | in Redmine |
| MS 4 | Link zum erstellten System | in Redmine |
| MS 4 | Liste mit Test-Accounts - Login/Passwort | in Redmine |
| MS 5 | Ergebnispräsentation | Video oder Link; maximal 20 Minuten, Demo maximal sieben Minuten |
| MS 6 | Projektbericht | Abgabe durch jedes Mitglied in Turnitin; Ticketkommunikation über Redmine |

Für jeden Liefergegenstand werden verantwortliche Person, Reviewer:in, Speicherort, Version und Abnahmestatus dokumentiert.

# Projektstrukturplan

Der Projektstrukturplan gliedert das Projekt in Arbeitspakete, die jeweils einem Meilenstein oder Liefergegenstand zugeordnet werden. Die technische Untergliederung wird im Rahmen von MS 3 durch die zuständigen Teammitglieder weiter konkretisiert.

| PSP-ID | Arbeitspaket | Bekannte Teilaufgaben und Ergebnisse |
| --- | --- | --- |
| 1.0 | Projektplanung und -steuerung | Terminplanung, Projektkonfiguration, Abstimmungen, Fortschrittskontrolle, Änderungs- und Risikomanagement |
| 1.1 | MS 0 – Meilensteinplan | Projektzeitraum festlegen, Meilensteine anordnen, Plan visualisieren und in Redmine bereitstellen |
| 1.2 | MS 1 – Projektkonfiguration | Vision, Team, Anforderungen, Lösungsansatz, Projektstruktur, Aufwand, Rollen, Infrastruktur und Risiken dokumentieren |
| 2.0 | MS 2 – Projektvideo | Inhalte auswählen, Ablauf planen, Sprecher:innen festlegen, Video aufnehmen, prüfen und bereitstellen |
| 3.0 | MS 3 – Entwicklungs- und Qualitätskonfiguration | Vorgehensmodell, Entwicklungsumgebung, Artefakte, technische Rollen, Qualitätsziele, Prüfverfahren und Liefergegenstände festlegen |
| 4.0 | Softwaresystem | Browserbasierte Anwendung implementieren, integrieren und bereitstellen |
| 4.1 | Entwicklungsumgebung und Infrastruktur | Repository-Struktur, Entwicklungsumgebung, Container, Datenbank, CI/CD und Hosting vorbereiten |
| 4.2 | Nutzer- und Zugriffsverwaltung | Registrierung, Anmeldung, Sitzungen, Mandantentrennung und Kontolöschung umsetzen |
| 4.3 | Personen und Anlässe | Personenverwaltung, Geburtstage, feste und benutzerdefinierte Anlässe sowie Zuordnungen umsetzen |
| 4.4 | Geschenke und Aufgaben | Geschenkideen, Statusübergänge, Historie, Anhänge, Notizen und Aufgaben umsetzen |
| 4.5 | Benachrichtigungen | Geburtstags- und Weihnachtsbenachrichtigungen, Scheduler, Versandstatus und Deduplizierung umsetzen |
| 4.6 | Teilen und Export | Widerrufbare Nur-Lese-Links sowie HTML-Darstellung beziehungsweise HTML-Export umsetzen |
| 4.7 | Geschenkideen-Vorschläge | Datenmerkmale, Vorschlagserzeugung, Ausschlussregeln sowie Übernahme und Verwerfung umsetzen |
| 5.0 | Qualitätssicherung | Anforderungen prüfen, Reviews durchführen sowie Unit-, Integrations-, Berechtigungs- und E2E-Tests erstellen und ausführen |
| 6.0 | MS 4 – Dokumentation und Bereitstellung | Benutzerhandbuch, fachliche, technische und betriebliche Dokumentation, Testabschlussbericht, Testkonten und erreichbares System bereitstellen |
| 7.0 | MS 5 – Ergebnispräsentation | Projektverlauf, Systemüberblick, Testergebnisse, Demo und Lessons Learned aufbereiten und als Video bereitstellen |
| 8.0 | MS 6 – Projektbericht | Individuelle Textbereiche erstellen, gemeinsame Redaktion durchführen, Titelblatt prüfen und Bericht in Turnitin einreichen |

# Aufwandsschätzung (grobe Schätzung auf Basis des Projektstrukturplans)

Die Aufwandsschätzung basiert auf den zum Zeitpunkt von MS 1 bekannten Arbeitspaketen. Technische Unsicherheiten, insbesondere bei Benachrichtigungen, Freigabelinks, Vorschlagserzeugung und Bereitstellung, werden durch eine zusätzliche Reserve berücksichtigt.

| PSP-ID | Arbeitspaket | Geschätzter Aufwand |
| --- | --- | ---: |
| 1.0–1.2 | Projektplanung und -steuerung einschließlich MS 0 und MS 1 | 40 h |
| 2.0 | Projektvideo MS 2 | 16 h |
| 3.0 | Entwicklungs- und Qualitätskonfiguration MS 3 | 32 h |
| 4.0–4.7 | Implementierung und technische Bereitstellung | 140 h |
| 5.0 | Qualitätssicherung und Tests | 35 h |
| 6.0 | Dokumentation und Bereitstellung MS 4 | 35 h |
| 7.0 | Ergebnispräsentation MS 5 | 20 h |
| 8.0 | Gemeinsamer Projektbericht MS 6 | 50 h |
|  | **Basisaufwand** | **368 h** |
|  | **Projektreserve: 15 %** | **55 h** |
|  | **Gesamtaufwand gerundet** | **423 h** |

Bei vier Teammitgliedern entspricht dies durchschnittlich rund 106 Stunden pro Person über den gesamten Projektzeitraum. Die tatsächliche Verteilung richtet sich nach Rolle, Vorerfahrung, Verfügbarkeit und Umfang der übernommenen Arbeitspakete. Die Reserve wird nicht von Beginn an einzelnen Aufgaben zugeordnet, sondern nur bei eingetretenen Risiken oder unerwartetem Mehraufwand verwendet.

Im wöchentlichen Teams-Termin werden geschätzter Restaufwand und verfügbare Kapazität verglichen. Zeichnet sich eine Überschreitung ab, werden Aufgaben neu verteilt oder nachrangige SOLL-Anforderungen reduziert.

# eingesetzte Systeme zu Erstellung der Lieferergebnisse und zum Management der einzelnen Aufgaben

| Zweck | System und verbindliche Nutzung |
| --- | --- |
| Übermittlung der Meilensteine und Tutorfeedback | **IU Redmine**; bei einer Abgabe wird das jeweilige Ticket auf **Feedback** gesetzt und dem Tutor zugewiesen |
| Regelmeetings, ausführliche Abstimmungen und Videoaufnahmen | **Microsoft Teams** |
| Kurzfristige Abstimmungen und wichtige Projektmeldungen | gemeinsame **Signal-Gruppe**; keine Passwörter, Zugangsdaten oder personenbezogenen Testdaten |
| Aufgaben und Zuständigkeiten | gemeinsame Festlegung in Teams; Dokumentation der Verantwortungen und wichtigen Entscheidungen in der versionierten Projektdokumentation |
| Quellcode und technische Dokumentation | **privates GitHub-Repository** mit Branches, Reviews und Pull Requests |
| Dokumentenerstellung | **Markdown im Repository**; finale Lieferfassungen werden als PDF exportiert |
| Daten- und Architekturmodellierung | **yEd/GraphML** beziehungsweise abgestimmtes Diagrammwerkzeug; relevante Modelle werden zusätzlich als Bild exportiert |
| Entwicklung | individuelle IDEs auf Grundlage einer gemeinsam dokumentierten und reproduzierbaren Projektumgebung |
| Automatisierte Prüfungen | vorgesehene CI-Funktion des GitHub-Repositorys für Linting, Tests und Build |
| Bereitstellung | containerisierte Hostingumgebung mit HTTPS, relationaler Datenbank und getrenntem Hintergrundprozess; endgültige Bestätigung in MS 3 |

# Rollen und Verantwortungen

Die operative Bearbeitung der Arbeitspakete erfolgt dezentral durch die jeweils verantwortlichen Teammitglieder. Wichtige Entscheidungen werden gemeinsam abgestimmt. Für kritische Ergebnisse wird zusätzlich eine prüfende Person festgelegt, damit kein Liefergegenstand ausschließlich durch seine erstellende Person kontrolliert wird.

| Teammitglied | Vorgesehene Rolle | Wesentliche Verantwortungen |
| --- | --- | --- |
| **Kevin Jordan Taghu** | Projektleitung und Datenanalyse | Überblick über Termine und Liefergegenstände, formale Bereitstellung in Redmine, Kommunikation mit dem Tutor sowie Unterstützung bei Datenmodellierung und Auswertung |
| **Julian Ammann** | Technische Leitung und Full-Stack-Entwicklung | Bestätigung der Systemarchitektur, Backend- und Frontendentwicklung, DevOps, CI/CD, Hosting und technische Integration |
| **Yin Yin Wu-Hanke** | Security und Frontendentwicklung | Sicherheits- und Datenschutzkonzept, Prüfung der Angriffsflächen und Berechtigungen sowie Unterstützung bei Frontend und Security-Tests |
| **Anton Hirsch** | Anforderungen, Dokumentation und Testunterstützung | Pflege der fachlichen Anforderungen, Mitwirkung am Datenmodell, Bearbeitung der Projekt- und Personalrisiken, Dokumentation, Nachvollziehbarkeit sowie Erstellung und Durchführung fachlicher Testfälle |

Die Projektleitung koordiniert den Gesamtüberblick, die formalen Abgaben und die Kommunikation mit dem Tutor. Operative Entscheidungen und Probleme werden zunächst durch die betroffenen Teammitglieder bearbeitet und bei projektweiter Bedeutung mit dem gesamten Team abgestimmt.

# Aufbau technische Infrastruktur

- Infrastruktur sollte via CI/CD deployed werden. Auf Cloud Provider oder eigene Hosting umgebung sprich vorhandener Server.
- Internetfacing Traefik Container der das Routing, TLS, Middlewares, via Docker-Providers (Labels) übernimmt. Dieser stellt zugleich auch das SSL-Zertifikat via Let's Encrypt aus.
- Frontend aus JavaScript Framework das seinen eigenen Docker Container bekommt, Node Server oder nginx beinhaltet.
- Backend geplant mit Python eigener Container da Scheduler und Backend logik getrennt laufen müssen.
- Backend greift auf DB zu Postgresql / MySQL.

![InfraStruktur](./images/infra-visualisierung.png)

# Personalmanagement

## Ressourcenplanung

- Jedes Mitglied nennt im nächsten Teammeeting seine realistische Wochenkapazität bis Ende Oktober.
- Arbeitspakete werden in kleine, innerhalb weniger Tage überprüfbare Aufgaben zerlegt.
- Kritische Bereiche erhalten eine eingewiesene Vertretung.
- Überlastung, Restaufwand und Blocker werden im Donnerstagstermin geprüft.
- Die letzten zwei Tage vor einem Meilenstein werden für Review, Korrektur, Export und Bereitstellung reserviert.

## Urlaub und Abwesenheit

- Bekannte Abwesenheiten werden möglichst zwei Wochen im Voraus bekannt gegeben.
- Kurzfristige Ausfälle werden unverzüglich mitgeteilt.
- Bei längerer Abwesenheit werden Bearbeitungsstand, offene Schritte und relevante Dateien schriftlich übergeben.
- Bei Ausfall einer Schlüsselperson werden Pflichtumfang und Vertretung zuerst gesichert. Eine Meilensteingefährdung wird frühzeitig mit dem Tutor abgestimmt.

## Projektbericht

Die Seitenverantwortung für MS 6 wird spätestens mit MS 3 festgelegt. Jedes Mitglied erstellt entsprechend der formalen Vorgaben einen zusammenhängenden, eindeutig zugeordneten Textteil von 7–10 Seiten. Eine gemeinsame Redaktion prüft Übergänge, Dopplungen, Quellen, Format und Titelblatt, ohne die individuelle Autorenschaft aufzuheben.

# Kommunikationsmanagement

## Bisherige Meetings

- **20.08.2026:** Vorstellungsrunde, Wahl von Kevin zur Projektleitung und gemeinsame Erarbeitung von MS 0.
- **26.08.2026:** Vorgezogenes zweites Meeting mit strukturellen Überlegungen und Erstellung eines ersten ER-Modells.
- **03.09.2026:** Prüfung des MS-1-Arbeitsstands und Beschluss, das Risikomanagement nach Projekt-/Personalrisiken, technischen Risiken sowie Informationssicherheits- und Datenschutzrisiken zu strukturieren.

## Regelkommunikation

- Das Team trifft sich grundsätzlich jeden Donnerstagabend für etwa 60 Minuten in Microsoft Teams.
- In den Regelmeetings werden Bearbeitungsstände, Blocker, nächste Aufgaben, Kapazitäten und bevorstehende Meilensteine besprochen.
- Die Signal-Gruppe dient kurzfristigen Abstimmungen, wichtigen Projektmeldungen und zeitkritischen Entscheidungen.
- Informationen mit Bedeutung für das gesamte Projekt werden an die gemeinsame Signal-Gruppe und nicht ausschließlich an die Projektleitung gesendet.
- Wesentliche Architektur-, Umfangs-, Termin- und Datenschutzentscheidungen werden anschließend kurz in der gemeinsamen Projektdokumentation festgehalten.
- Passwörter, Zugangsdaten und personenbezogene Testdaten werden weder über Signal noch im Repository geteilt.
- Die Projektleitung übernimmt die formale Bereitstellung der Liefergegenstände und die Kommunikation mit dem Tutor. Operative Abstimmungen erfolgen direkt zwischen den beteiligten Teammitgliedern.

# Risikomanagement

Das Risikomanagement wird während des gesamten Projekts fortgeführt. Risiken werden anhand ihrer **Eintrittswahrscheinlichkeit** und ihrer **Auswirkung** jeweils als niedrig, mittel oder hoch bewertet.

| Eintrittswahrscheinlichkeit / Auswirkung | niedrig | mittel | hoch |
| --- | --- | --- | --- |
| **niedrig** | niedrig | niedrig | mittel |
| **mittel** | niedrig | mittel | hoch |
| **hoch** | mittel | hoch | hoch |

Risiken mit hoher Priorität werden unmittelbar behandelt. Risiken mit mittlerer Priorität werden spätestens im nächsten Regelmeeting überprüft. Risiken mit niedriger Priorität werden dokumentiert und bei wesentlichen Änderungen erneut bewertet.

Die Risikoliste wird als Bestandteil der Projektdokumentation im Repository versioniert. Wichtige oder zeitkritische Risiken werden unmittelbar in der gemeinsamen Signal-Gruppe mitgeteilt. Die operative Behandlung übernimmt die für das betroffene Arbeitspaket zuständige Person gemeinsam mit den unmittelbar beteiligten Mitgliedern.

Die Projektleitung wird insbesondere dann einbezogen, wenn ein Meilenstein gefährdet ist oder eine Abstimmung mit dem Tutor erforderlich wird. Redmine wird nicht zur internen Risikoverwaltung, sondern ausschließlich zur formalen Übermittlung der Meilensteine verwendet.

## Projekt- und Personalrisiken

| ID | Risiko | Bewertung | Vorbeugung und Frühindikator | Reaktion |
| --- | --- | --- | --- | --- |
| PM-01 | Ein Artefakt oder Liefergegenstand wird verspätet oder nicht prüffähig fertiggestellt. | Eintritt: mittel; Auswirkung: hoch | Verantwortliche Person, Reviewperson und interne Frist werden festgelegt. Die Fertigstellung soll mindestens zwei Tage vor dem Meilenstein erfolgen. | Das Team wird über Signal informiert, priorisiert die offenen Aufgaben neu und stellt zunächst den Pflichtumfang sicher. |
| PM-02 | Ein Teammitglied fällt kurzfristig oder längerfristig aus. | Eintritt: mittel; Auswirkung: hoch | Bearbeitungsstände und offene Schritte werden dokumentiert. Kritische Bereiche erhalten eine eingewiesene Vertretung. | Die Aufgaben werden gemeinsam neu verteilt. Reicht die Kapazität nicht aus, werden zunächst SOLL-Anforderungen reduziert. |
| PM-03 | Der Aufwand wurde unterschätzt oder die Teamkapazität reicht nicht aus. | Eintritt: hoch; Auswirkung: hoch | Restaufwand und Kapazität werden wöchentlich verglichen. Die Projektreserve wird nicht vorab verplant. | Arbeitspakete werden weiter zerlegt, neu verteilt oder im Umfang reduziert. |
| PM-04 | Unklare Zuständigkeiten oder Entscheidungen führen zu Doppelarbeit. | Eintritt: mittel; Auswirkung: mittel | Für jedes Arbeitspaket werden verantwortliche und prüfende Personen festgelegt. Wesentliche Entscheidungen werden dokumentiert. | Offene Fragen werden in Signal gestellt und bei Bedarf in einem kurzfristigen Teams-Termin entschieden. |
| PM-05 | Zeitdruck führt zu fehlenden Reviews oder unzureichenden Tests. | Eintritt: mittel; Auswirkung: hoch | Review, Test und Korrektur werden als eigenständige Arbeitsschritte eingeplant. | Neue Funktionen werden gegebenenfalls gestoppt. Die verbleibende Zeit wird auf Fehler, Sicherheitsprobleme und MUSS-Anforderungen konzentriert. |
| PM-06 | Wichtige Informationen erreichen nicht alle Teammitglieder. | Eintritt: mittel; Auswirkung: mittel | Projektweit relevante Nachrichten werden in der gemeinsamen Signal-Gruppe veröffentlicht. | Unterschiedliche Annahmen werden vor der weiteren Bearbeitung gemeinsam geklärt. |
| PM-07 | Das Projekt übernimmt mehr MUSS-Anforderungen, als im vorgesehenen Zeitraum zuverlässig umgesetzt werden können. | Eintritt: hoch; Auswirkung: hoch | Aufwand und technisches Risiko jeder Anforderung werden spätestens in MS 3 bewertet. | Erweiterungen werden als SOLL eingeordnet oder vereinfacht. Die Anforderungen des Themenblatts bleiben vorrangig. |
| PM-08 | Quellcode, Dokumentation oder andere Arbeitsergebnisse gehen verloren oder können keinem eindeutigen Stand zugeordnet werden. | Eintritt: niedrig; Auswirkung: hoch | Arbeitsergebnisse werden regelmäßig in das GitHub-Repository übertragen. Abgabestände erhalten eindeutige Versionsbezeichnungen beziehungsweise Tags. | Der letzte nachvollziehbare Stand wird wiederhergestellt und vor der weiteren Bearbeitung gemeinsam geprüft. |

## Technische Risiken
| ID | Risiko | Bewertung | Vorbeugung und Frühindikator | Reaktion |
| --- | --- | --- | --- | --- |
| TR-01 | Merge-Konflikte durch parallele Arbeit mehrerer Teammitglieder im gleichen Codebereich. | Eintritt: hoch; Auswirkung: mittel | Feature-Branches werden klein gehalten und regelmäßig gemerged, um Divergenzen frühzeitig sichtbar zu machen. Klare Absprache im Team, wer an welchen Komponenten arbeitet. | Der Merge-Konflikt wird von den betroffenen Personen gemeinsam aufgelöst, bevor der Pull Request freigegeben wird. |
| TR-02 | Fehlerhafter oder ungeprüfter Code gelangt ohne vorheriges Review in den main-Branch | Eintritt: mittel; Auswirkung: hoch | Github Branch Protection Rule für main: kein direkter Push möglich, Pull Request mit mindestens einer Review-Freigabe durch ein anderes Teammitglied als dem Ersteller des Pull Request erforderlich. | Der Pull Request wird zurückgewiesen oder mit Änderungswünschen versehen, bis Review erfolgreich erfolgt ist. |
| TR-03 | Die Authentifizierung (Login/Session-Handling) schlägt fehl oder lässt sich nicht wie geplant umsetzen | Eintritt: mittel; Auswirkung: hoch | Frühzeitiger Proof-of-Concept für die Authentifizierung. | Bei anhaltenden Problemen wird auf eine einfachere, gut dokumentierte Alternativlösung umgestiegen. |
| TR-04 | Selbst gehosteter Server fällt aus z. B. durch Stromausfall, Hardwaredefekt, Internetausfall oder ungeplanter Neustart | Eintritt: mittel; Auswirkung: hoch | Regelmäßige Backups von Datenbank und Docker-Volumes, Deployment-Schritte werden vollständig dokumentiert. | Bei kurzfristigem Ausfall wird der Server vom hostenden Teammitglied neu gestartet bzw. das Deployment anhand der Dokumentation wiederhergestellt, bei längerem Ausfall wird auf eine alternative Hosting-Option ausgewichen. |


## Informationssicherheit und Datenschutz
| ID | Risiko | Bewertung | Vorbeugung und Frühindikator | Reaktion |
| --- | --- | --- | --- | --- |
| ISD-01 | Es werden personenbezogene Daten Dritter (Name, Geburtstag der beschenkten Personen) gespeichert, die diesen Personen nicht bekannt ist und der sie nicht zugestimmt haben | Eintritt: mittel; Auswirkung: hoch | Im Projektbericht wird dokumentiert, dass es sich um einen MVP handelt und ausschließlich mit Testdaten statt echten Personendaten gearbeitet wird. | Werden im Projektverlauf doch reale Personendaten eingegeben, werden diese vor der Abgabe durch anonymisierte Testdaten ersetzt. |
