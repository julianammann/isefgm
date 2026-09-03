# Projektvision

Der **Geschenke-Manager** wird als datenschutzorientierte, browserbasierte Webanwendung konzipiert und prototypisch umgesetzt. Die Anwendung unterstützt Nutzer:innen dabei, Personen, Anlässe, Geschenkideen, bereits verschenkte Geschenke und noch offene Aufgaben an einer zentralen Stelle zu verwalten. Damit sollen vergessene Anlässe, doppelte Geschenke und kurzfristiger Beschaffungsstress vermieden werden.

Personen, Anlässe und Geschenkideen/Geschenke werden unabhängig voneinander angelegt und bei Bedarf flexibel verknüpft. Eine Idee kann dadurch sofort erfasst werden, auch wenn Empfänger:in oder Anlass noch nicht feststehen. Umgekehrt kann ein Anlass geplant werden, bevor Personen oder Geschenke ausgewählt wurden.

Automatische Benachrichtigungen weisen auf bevorstehende Anlässe und noch nicht besorgte Geschenke hin. Widerrufbare Freigabelinks ermöglichen das kontrollierte Teilen ausgewählter Ideen. Weitere Vorschläge werden aus anonymisierten und aggregierten Merkmalen tatsächlich verschenkter Geschenke abgeleitet. Personenbezogene Daten anderer Konten bleiben dabei getrennt und werden nicht offengelegt.

# Vorstellung des Teams

| Teammitglied | Foto | Kurzprofil | Skills |
| --- | --- | --- | --- |
| **Yin Yin Wu-Hanke** | *Foto ergänzen* | Detection Engineer | Frontendentwicklung, Security |
| **Julian Ammann** | *Foto ergänzen* | Senior Full Stack Developer | Frontend- & Backendentwicklung, DevOps, Systemarchitektur |
| **Anton Hirsch** | *Foto ergänzen* | Informatikstudent (B.Sc) | Grundlagen in Python, Java, C++, SQL und ChatGPT |
| **Kevin Jordan Taghu** | *Foto ergänzen* | Data Analyst | Frontendentwicklung, Datenmodellierung, Reporting, Datenvisualisierung, Datenbereinigung |

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
- Redmine ist das führende System für Aufgaben, Meilensteine, Abgaben und Tutorfeedback.
- Quellcode und technische Dokumentation werden in einem privaten Git-Repository versioniert.
- Features und Fehlerkorrekturen werden in eigenen Branches bearbeitet und über Pull Requests in den geschützten Hauptbranch übernommen.
- Architektur-, Datenschutz-, Umfangs- und Terminentscheidungen werden schriftlich festgehalten.

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

# Aufwandsschätzung (grobe Schätzung auf Basis des Projektstrukturplans)

# eingesetzte Systeme zu Erstellung der Lieferergebnisse und zum Management der einzelnen Aufgaben

| Zweck | System und verbindliche Nutzung |
| --- | --- |
| Meilensteine, Aufgaben, Tutorfeedback und Abgaben | **IU Redmine** als führendes Projektmanagementsystem |
| Quellcode und technische Versionierung | **privates GitHub-Repository** mit Branches und Pull Requests |
| Regelmeetings und Videoaufnahmen | **Microsoft Teams** |
| kurzfristige Abstimmung | **Signal-Gruppe**, jedoch keine Passwörter oder personenbezogenen Testdaten |
| Dokumentation | **Markdown im Repository**, finale Lieferfassung als PDF |
| Entwicklung | individuelle IDE sowie eine gemeinsam dokumentierte, reproduzierbare Projektumgebung |
| automatisierte Prüfungen | CI-Funktion des Git-Repositorys für Linting, Tests und Build |
| Bereitstellung | Hostingdienst mit HTTPS, relationaler Datenbank und Hintergrundprozess; verbindliche Auswahl bis MS 3 |

# Rollen und Verantwortungen

# Aufbau technische Infrastruktur

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

- **20.08.2026:** Vorstellungsrunde, Wahl von Kevin zum Teamleiter und gemeinsame Erarbeitung von MS 0.
- **26.08.2026:** vorgezogenes zweites Meeting mit strukturellen Überlegungen und erstem ER-Modell.

## Regelkommunikation

- Das Team trifft sich jeden Donnerstagabend grundsätzlich für 60 Minuten in Microsoft Teams.
- Die Signal-Gruppe dient kurzfristigen Absprachen.

# Risikomanagement
