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
| `SMTP_HOST` | `localhost` | SMTP server host for outgoing mail. The default points at a local Mailpit. |
| `SMTP_PORT` | `1025` | SMTP server port. Typical values: 1025 for Mailpit, 587 for STARTTLS, 465 for implicit TLS. |
| `SMTP_SECURITY` | `none` | Transport security for SMTP. `none` for Mailpit, `starttls` for port 587, `tls` for port 465 (implicit TLS, e.g. Resend). |
| `SMTP_USERNAME` | `None` | SMTP login name. Leave unset when the server needs no authentication. |
| `SMTP_PASSWORD` | `None` | SMTP login password. Never shown in `repr()`; log tracebacks omit local variables. |
| `SMTP_FROM` | `Geschenke-Manager <noreply@isefgm.localhost>` | Sender address on outgoing mail, in `Name <address>` form. Production sets it via the deployment (SMTP_FROM). |
| `SMTP_TIMEOUT_SECONDS` | `30` | Timeout in seconds for connecting to and talking to the SMTP server. |
| `UPLOADS_DIR` | `data/uploads` | Storage for image uploads; a volume in production. The database only holds metadata. |
| `SESSION_TTL_DAYS` | `14` | Session lifetime in days; extended on every use, up to `SESSION_MAX_LIFETIME_DAYS`. |
| `SESSION_MAX_LIFETIME_DAYS` | `30` | Hard upper bound on a session's age in days, counted from login, however often the session is used. After that the user must log in again. |
| `REGISTRATION_ENABLED` | `False` | `true` opens `POST /api/v1/auth/register` and the sign-up page; otherwise the endpoint returns 403 and the frontend hides the link (it reads the same variable). Accounts can always be created with `mise run create-user`. |
| `ORIGIN` | `http://localhost:3000` | Public address of the app, used for links in mails. Same value as the frontend's `ORIGIN`. |
