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
