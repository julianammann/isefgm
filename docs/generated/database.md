<!-- Generated from the code by `mise run docs`. Do not edit by hand. -->

# Database

Tables and columns from `giftmanager.models`. Relationships and normalisation: `docs/datenmodell.md`. The comments are also stored in PostgreSQL (`\d+ <table>`).

## user_account

User account (F-01). Every domain table belongs to exactly one account via owner_id; deleting the account deletes all of its data (F-17).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. (PK) |
| `email` | VARCHAR(320) | no | Login name. Stored lowercased and unique. (unique) |
| `password_hash` | VARCHAR(255) | no | Argon2id hash of the password (Q-03). The password itself is never stored. |
| `display_name` | VARCHAR(100) | no | Display name in the UI and in notifications. |
| `status` | VARCHAR(16) | no | `active` or `deleted`. `deleted` only marks an account while it is being deleted. |
| `created_at` | TIMESTAMP WITH TIME ZONE | no | Creation time (UTC), set by the database (Q-08). |

## gift

Gift idea of an account (F-05): the reusable content of an idea. Visible only to its owner (Q-01); deleted together with the account (F-17).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. (PK) |
| `owner_id` | UUID | no | Account the gift idea belongs to. Deleted together with the account. (FK → user_account.id) |
| `title` | VARCHAR(200) | no | Short title, the only required field for quick capture. |
| `description` | TEXT | yes | Free-text description. Optional. |
| `price_from` | NUMERIC(10, 2) | yes | Lower end of the price range in `currency`. Optional. |
| `price_to` | NUMERIC(10, 2) | yes | Upper end of the price range in `currency`. Optional. |
| `currency` | VARCHAR(3) | yes | ISO 4217 code of the price range currency, e.g. EUR. Set exactly when a price is set. |
| `category` | VARCHAR(16) | no | Kind of gift, feature for suggestions (F-16). `other` when not chosen. |
| `created_at` | TIMESTAMP WITH TIME ZONE | no | Creation time (UTC), set by the database (Q-08). |

## occasion_type

Kind of occasion (F-03). owner_id NULL marks the system-wide types Geburtstag and Weihnachten, created by a migration and read-only for users.

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. (PK) |
| `owner_id` | UUID | yes | Account that defined the type. NULL for system-wide types. (FK → user_account.id) (Index) |
| `name` | VARCHAR(100) | no | Display name, e.g. Geburtstag. |
| `default_recurrence` | VARCHAR(16) | no | `none` or `yearly`. Suggested recurrence for occasions of this type. |

## person

Person the account owner gives gifts to (F-02). Visible only to its owner (Q-01); deleted together with the account (F-17).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. (PK) |
| `owner_id` | UUID | no | Account the person belongs to. Deleted together with the account. (FK → user_account.id) |
| `name` | VARCHAR(100) | no | Name as the owner calls the person. |
| `birthday` | DATE | yes | Birthday as a plain date, optional. Source for birthday reminders. |
| `relationship` | VARCHAR(100) | yes | Free-text relationship, e.g. sister or colleague. Optional. |
| `notes` | TEXT | yes | Free-text notes, e.g. hobbies or sizes. Optional. |
| `created_at` | TIMESTAMP WITH TIME ZONE | no | Creation time (UTC), set by the database (Q-08). |

## user_session

Server-side session. One cookie token maps to exactly one row; logging out deletes the row.

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. (PK) |
| `user_id` | UUID | no | Account the session belongs to. Deleted together with the account. (FK → user_account.id) (Index) |
| `token_hash` | VARCHAR(64) | no | SHA-256 of the cookie token. Only the browser knows the token itself. (unique) |
| `expires_at` | TIMESTAMP WITH TIME ZONE | no | Expiry time (UTC). The session is rejected afterwards. |
| `last_seen_at` | TIMESTAMP WITH TIME ZONE | no | Last use (UTC), updated at most every five minutes. |
| `created_at` | TIMESTAMP WITH TIME ZONE | no | Creation time (UTC), set by the database (Q-08). |

## attachment

Labelled link or image on a gift idea (F-07), told apart by kind. Visible only to the owner of the idea (Q-01); deleted together with the idea and the account (F-17).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. Also the list order: oldest attachment first. (PK) |
| `gift_id` | UUID | no | Gift idea the attachment belongs to. Deleting the idea deletes it. (FK → gift.id) (Index) |
| `kind` | VARCHAR(16) | no | `link` or `image`. |
| `label` | VARCHAR(100) | no | Label, e.g. Thalia or Bild vom Laden. |
| `url` | VARCHAR(2048) | yes | Absolute http or https URL. Required for links, NULL for images. |

## gift_person

Possible recipients of a gift idea (F-04), n:m. Deleting the idea or the person removes only the link. Actual recipients belong to a gifting (F-06).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `gift_id` | UUID | no | Gift idea. Deleting it deletes the link. (PK) (FK → gift.id) |
| `person_id` | UUID | no | Possible recipient. Deleting the person deletes the link. (PK) (FK → person.id) (Index) |

## note

Labelled note on a gift idea (F-07). Visible only to the owner of the idea (Q-01); deleted together with the idea and the account (F-17).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. Also the list order: oldest note first. (PK) |
| `gift_id` | UUID | no | Gift idea the note belongs to. Deleting the idea deletes the note. (FK → gift.id) (Index) |
| `label` | VARCHAR(100) | no | Label, e.g. Größe. |
| `text` | TEXT | no | Text of the note, up to 2000 characters. |

## occasion

Occasion of an account (F-03). Stores the rule (date and recurrence); a concrete year is stored where the occasion is used. Visible only to its owner (Q-01).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. (PK) |
| `owner_id` | UUID | no | Account the occasion belongs to. Deleted together with the account. (FK → user_account.id) (Index) |
| `occasion_type_id` | UUID | yes | Type of the occasion. NULL for an own occasion without a type. (FK → occasion_type.id) (Index) |
| `name` | VARCHAR(100) | no | Title, e.g. Hochzeitstag. |
| `date` | DATE | no | Date as a plain calendar date (Q-08). First occurrence for yearly ones. |
| `recurrence` | VARCHAR(16) | no | `none` (once) or `yearly` (every year on the same day). |

## gift_occasion

Possible occasions of a gift idea (F-04), n:m. Deleting the idea or the occasion removes only the link. The concrete occasion belongs to a gifting (F-06).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `gift_id` | UUID | no | Gift idea. Deleting it deletes the link. (PK) (FK → gift.id) |
| `occasion_id` | UUID | no | Possible occasion. Deleting the occasion deletes the link. (PK) (FK → occasion.id) (Index) |

## gifting

Concrete use of a gift idea (F-06), with its own status, actual recipients, occasion and dates. Belongs to the account of the gift idea; deleted together with the account (F-17).

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `id` | UUID | no | Primary key, UUIDv7. (PK) |
| `gift_id` | UUID | no | CASCADE only for deleting the account (F-17), which deletes the gift in the same statement. Through the API an idea with giftings is not deletable: delete_gift answers 409 (test_idea_with_giftings_cannot_be_deleted). RESTRICT here would make test_deleting_the_account_deletes_its_giftings fail. (FK → gift.id) (Index) |
| `status` | VARCHAR(16) | no | Progress of the gifting. Defaults to 'idea'. |
| `occasion_id` | UUID | yes | Same reasoning as gift_id: the API answers 409 when an occasion in use is deleted (directly or as a derived birthday), the cascade only runs for F-17. (FK → occasion.id) (Index) |
| `occasion_date` | DATE | yes | Date. Concrete date of the occasion, e.g. Christmas 2026 for a yearly occasion (Q-08: plain calendar date, no time zone). |
| `given_on` | DATE | yes | Date. Day the gift was given; set exactly when status is `given`. |
| `created_at` | TIMESTAMP WITH TIME ZONE | no | Creation time (UTC), set by the database (Q-08). |

## person_occasion

People an occasion concerns (F-04), n:m. Deleting the person or the occasion removes only the link.

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `person_id` | UUID | no | Person the occasion concerns. Deleting the person deletes the link. (PK) (FK → person.id) |
| `occasion_id` | UUID | no | Occasion. Deleting it deletes the link. (PK) (FK → occasion.id) (Index) |

## gifting_person

Actual recipients of a gifting (F-06), n:m. Several people share one joint gift. Deleting the gifting or the person removes only the link.

| Column | Type | Nullable | Description |
| --- | --- | --- | --- |
| `gifting_id` | UUID | no | Gifting. Deleting it deletes the link. (PK) (FK → gifting.id) |
| `person_id` | UUID | no | Actual recipient. Deleting a person only removes them as a recipient, the gifting remains (test_deleting_a_recipient_removes_them_from_the_gifting). (PK) (FK → person.id) (Index) |
