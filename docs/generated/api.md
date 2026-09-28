<!-- Generated from the code by `mise run docs`. Do not edit by hand. -->

# API

Base URL `/api/v1`; errors are problem details (RFC 9457). Field descriptions and examples: `frontend/openapi.json` or `/docs`.

## auth

Create, log in to, log out of and delete an account (F-01, F-17). The session lives on the server; the browser only holds a cookie.

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `DELETE /api/v1/auth/account` | `authDeleteAccount` | Delete account | Deletes the account with all of its data (F-17) and ends the session. Cannot be undone. | 204, 401 |
| `POST /api/v1/auth/login` | `authLogin` | Log in | Checks e-mail and password and sets the session cookie on success. Wrong credentials and unknown addresses get the same 401 response in the same time. When too many logins and registrations are already being checked, returns 503 at once with a Retry-After header; retry a few seconds later. | 200, 401, 422, 503 |
| `POST /api/v1/auth/logout` | `authLogout` | Log out | Revokes the session on the server and clears the cookie. Idempotent: also works without a cookie or with one that is no longer valid. | 204 |
| `POST /api/v1/auth/logout-all` | `authLogoutAll` | Log out everywhere | Revokes every session of the account on every device, this one included, and clears the cookie. For a lost device or a cookie that may have been stolen. | 204, 401 |
| `GET /api/v1/auth/me` | `authMe` | Current account | Returns the account of the current session. The frontend calls it on every page request to determine the login state. | 200, 401 |
| `POST /api/v1/auth/register` | `authRegister` | Create account | Creates an account and logs it in right away: the response sets the session cookie. Returns 403 while registration is closed (`REGISTRATION_ENABLED`). The e-mail address is stored lowercased; an address that is already registered returns 409. When too many logins and registrations are already being checked, returns 503 at once with a Retry-After header; retry a few seconds later. | 201, 403, 409, 422, 503 |

## health

Liveness and readiness for container healthchecks and Traefik.

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/health/live` | `healthLive` | Process is up | Answers as soon as the process accepts requests; does not touch the database. Target of the container healthcheck. | 200 |
| `GET /api/v1/health/ready` | `healthReady` | Database reachable | Runs `SELECT 1`. Without a database it returns `status: degraded` with HTTP 200, so that Traefik keeps the container in rotation while it is still starting. | 200 |
