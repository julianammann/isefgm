<!-- Generated from the code by `mise run docs`. Do not edit by hand. -->

# Configuration

Environment variables, read from `.env` in the repo root (template `.env.example`) or from the process environment.

| Variable | Default | Meaning |
| --- | --- | --- |
| `APP_NAME` | `Geschenke-Manager API` | Title in OpenAPI and in the Swagger UI. |
| `APP_ENV` | `production` | `development` enables `/docs`, `/openapi.json` and console logs and sends the session cookie as `session` without `Secure`; `production` and `test` write JSON logs and send it as `__Host-session` with `Secure`. Unset means `production`; `mise run dev` and `compose.override.yaml` set `development`. |
| `LOG_LEVEL` | `INFO` | Log threshold for the app, Uvicorn, SQLAlchemy and Alembic. |
| `DATABASE_URL` | `postgresql+asyncpg://app:app@localhost:5432/app` | PostgreSQL connection. The `asyncpg` driver is required. |
| `DEFAULT_TIMEZONE` | `Europe/Berlin` | Time zone in which the scheduler evaluates calendar dates (birthdays, occasions). Storage is in UTC (Q-08). |
| `UPLOADS_DIR` | `data/uploads` | Storage for image uploads; a volume in production. The database only holds metadata. |
| `SESSION_TTL_DAYS` | `14` | Session lifetime in days; extended on every use, up to `SESSION_MAX_LIFETIME_DAYS`. |
| `SESSION_MAX_LIFETIME_DAYS` | `30` | Hard upper bound on a session's age in days, counted from login, however often the session is used. After that the user must log in again. |
