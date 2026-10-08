# Datenmodell

Verbindliche Vorlage für `backend/src/giftmanager/models/`. Ersetzt inhaltlich das unvollständige `ER-Modell/ER-Modell.graphml` und ist mit der Tabelle „Vorgesehenes Zielmodell“ aus MS 1 abgeglichen. Tabellen- und Spaltennamen sind Englisch (Code-Sprache), die Beschreibung Deutsch.

Konventionen: Primärschlüssel `id` als UUID (v7, clientseitig), Tabellen heißen `user_account` und `user_session`, weil `user` in PostgreSQL reserviert ist, technische Zeitpunkte `timestamptz` in UTC, Kalenderdaten `date` (Q-08). Jede kontogebundene Tabelle hat `owner_id → user_account.id ON DELETE CASCADE` mit Index (Q-01, F-17). Abhängige Tabellen kaskadieren über ihre Elterntabelle.

```mermaid
erDiagram
    user_account ||--o| user_profile : "hat"
    user_account ||--o{ user_session : "hat"
    user_account ||--o{ person : "besitzt"
    user_account ||--o{ occasion_type : "definiert (eigene)"
    user_account ||--o{ occasion : "besitzt"
    user_account ||--o{ gift : "besitzt"
    user_account ||--o{ share_link : "besitzt"
    user_account ||--o{ suggestion : "erhält"
    user_account ||--o{ notification : "erhält"

    occasion_type ||--o{ occasion : "typisiert"
    person }o--o{ occasion : "person_occasion"
    gift }o--o{ person : "gift_person (mögliche Empfänger)"
    gift }o--o{ occasion : "gift_occasion (mögliche Anlässe)"

    gift ||--o{ gifting : "wird verwendet als"
    gifting }o--o{ person : "gifting_person (Empfänger)"
    occasion |o--o{ gifting : "konkreter Anlass"
    gifting ||--o{ task : "hat"

    gift ||--o{ note : "hat"
    gift ||--o{ attachment : "hat"

    share_link }o--o{ person : "share_link_person"
    person |o--o{ suggestion : "Zielperson"

    user_account {
        uuid id PK
        text email UK
        text password_hash
        text display_name
        text status "active | deleted"
        timestamptz created_at
    }
    user_profile {
        uuid user_id PK,FK
        text timezone
        text color_scheme
        jsonb notification_settings
        jsonb accessibility_settings
    }
    user_session {
        uuid id PK
        uuid user_id FK
        text token_hash UK
        timestamptz created_at
        timestamptz expires_at
        timestamptz last_seen_at
    }
    person {
        uuid id PK
        uuid owner_id FK
        text name
        date birthday "nullable"
        text relationship "nullable"
        text notes "nullable"
        timestamptz created_at
    }
    occasion_type {
        uuid id PK
        uuid owner_id FK "NULL = systemweit"
        text name
        text default_recurrence "none | yearly"
    }
    occasion {
        uuid id PK
        uuid owner_id FK
        uuid occasion_type_id FK
        text name
        date date
        text recurrence "none | yearly"
    }
    person_occasion {
        uuid person_id PK,FK
        uuid occasion_id PK,FK
    }
    gift {
        uuid id PK
        uuid owner_id FK
        text title
        text description "nullable"
        numeric price_from "nullable"
        numeric price_to "nullable"
        text currency "nullable, ISO 4217, nur mit Preis, default EUR"
        text category "für F-16: books | games | experience | clothing | tech | food | home | voucher | other, default other"
        timestamptz created_at
    }
    gift_person {
        uuid gift_id PK,FK
        uuid person_id PK,FK
    }
    gift_occasion {
        uuid gift_id PK,FK
        uuid occasion_id PK,FK
    }
    gifting {
        uuid id PK
        uuid gift_id FK
        text status "idea | planned | acquired | given"
        uuid occasion_id FK "nullable bis planned"
        date occasion_date "nullable, konkreter Termin z.B. Weihnachten 2026"
        date given_on "nullable, Pflicht bei given"
        timestamptz created_at
    }
    gifting_person {
        uuid gifting_id PK,FK
        uuid person_id PK,FK
    }
    task {
        uuid id PK
        uuid gifting_id FK
        text title
        text status "open | in_progress | done | discarded"
        date due_on "nullable"
        timestamptz created_at
    }
    note {
        uuid id PK
        uuid gift_id FK
        text label
        text text
    }
    attachment {
        uuid id PK
        uuid gift_id FK
        text kind "link | image"
        text url "bei link"
        text storage_path "bei image"
        text mime_type "bei image"
        int size_bytes "bei image"
        text label
    }
    share_link {
        uuid id PK
        uuid owner_id FK
        text token_hash UK
        bool active
        timestamptz expires_at "nullable"
        timestamptz created_at
    }
    share_link_person {
        uuid share_link_id PK,FK
        uuid person_id PK,FK
    }
    suggestion {
        uuid id PK
        uuid owner_id FK
        uuid target_person_id FK
        text title
        text reason
        text status "open | accepted | dismissed"
        timestamptz created_at
    }
    notification {
        uuid id PK
        uuid owner_id FK
        text type "birthday | christmas | occasion"
        text reference_type "person | occasion"
        uuid reference_id
        date event_date
        timestamptz scheduled_for
        text status "planned | sending | sent | failed"
        timestamptz claimed_at "nullable"
        timestamptz sent_at "nullable"
        text error "nullable"
        text dedup_key UK
    }
```

## Geschäftsregeln, die das Schema absichert

| Regel | Umsetzung |
|---|---|
| Eine Idee kann ohne Empfänger und Anlass existieren (F-04, F-05) | `gift_person`, `gift_occasion` optional; `gifting.occasion_id` nullable |
| Schnellerfassung einer Idee nur mit Titel (F-05) | übrige `gift`-Spalten nullable oder mit Default: `category` `other` |
| Eine Währung gibt es nur zu einem Preis (F-05) | Check-Constraint `ck_gift_currency_with_price` auf `(currency IS NULL) = (price_from IS NULL AND price_to IS NULL)`; die API setzt `EUR`, wenn ein Preis ohne Währung kommt, und verwirft die Währung ohne Preis |
| Gemeinsames Geschenk an mehrere Personen (F-04, F-06) | eine `gifting`-Zeile, mehrere `gifting_person`-Zeilen |
| Unabhängige Beschenkungen derselben Idee | mehrere `gifting`-Zeilen je `gift` |
| Bei `given` sind Empfänger, Anlass, Termin, Verschenkdatum Pflicht (F-06) | Check-Constraint `ck_gifting_given_complete` auf `status <> 'given' OR (occasion_id IS NOT NULL AND occasion_date IS NOT NULL AND given_on IS NOT NULL)`; mindestens ein Empfänger wird im Service geprüft |
| Weihnachten 2026 ≠ Weihnachten 2027 | `gifting.occasion_date` trägt den konkreten Termin, `occasion` nur die Regel |
| Kein Doppelversand (F-13, Q-02) | `UNIQUE(dedup_key)` auf `notification` |
| Freigabelink nicht erratbar, widerrufbar, ablaufend (F-14) | 256-Bit-Token, nur `token_hash` gespeichert, `active`, `expires_at` |
| Kontolöschung löscht alles (F-17) | `ON DELETE CASCADE` auf allen `owner_id` und auf `user_session.user_id`; Dateien aus `attachment.storage_path` werden nach dem Commit gelöscht |
| Geburtstag nur zusammen mit der Person (F-03, F-04) | Quelle ist `person.birthday`; der Service pflegt daraus genau einen `occasion` vom Typ „Geburtstag“ (jährlich, Datum = Geburtsdatum), verknüpft über `person_occasion` mit genau dieser Person. Über die API ist der Typ nicht wählbar (422) und ein solcher Anlass nicht änderbar oder löschbar (409) |
| Systemweite Anlasstypen (F-03) | `occasion_type.owner_id IS NULL`; „Geburtstag“ und „Weihnachten“ per Daten-Migration |
| Vorschläge nur aus aggregierten Merkmalen (F-16, Q-04) | Aggregation über `gift.category`, Preisband aus `price_from/price_to`, `occasion_type.name`; nie über `title`, `description`, `note`, `attachment` |

## Indizes

Neben den Primär- und Unique-Schlüsseln: Index auf jedem `owner_id`, jedem Fremdschlüssel, `notification(status, scheduled_for)` für den Scheduler, `person(owner_id, birthday)` für die Geburtstagsplanung und `gift(owner_id, created_at)` für die Ideenliste.

## Offene Punkte

- Preisband für F-16: Grenzen festlegen (Vorschlag: `<20`, `20–50`, `50–100`, `>100`).
- Altersgruppe für F-16 wird zur Laufzeit aus `person.birthday` abgeleitet, nicht gespeichert.
