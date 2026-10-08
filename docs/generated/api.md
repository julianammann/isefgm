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

## gifts



| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/gifts` | `listGifts` | List gift ideas | Returns the gift ideas of the current account, newest first, one page at a time. `total` counts all gift ideas of the account. | 200, 401, 422 |
| `POST /api/v1/gifts` | `createGift` | Create gift idea | Creates a gift idea for the current account. Only the title is required, so an idea can be captured in one step: empty optional fields are stored as null, `currency` defaults to EUR and `category` to `other`. The creation time is set by the server. `person_ids` and `occasion_ids` link the idea to people and occasions of the account; an ID of another account returns 404, like a missing one, and nothing is saved. | 201, 401, 404, 422 |
| `GET /api/v1/gifts/{gift_id}` | `getGift` | Show gift idea | Returns one gift idea of the current account. A gift idea of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/gifts/{gift_id}` | `updateGift` | Update gift idea | Replaces all fields of the gift idea, including its links: a field left out is reset to null, its default or an empty list. The frontend sends the whole form. `person_ids` and `occasion_ids` link the idea to people and occasions of the account; an ID of another account returns 404, like a missing one, and nothing is saved. A gift idea of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/gifts/{gift_id}` | `deleteGift` | Delete gift idea | Deletes the gift idea. Cannot be undone. A gift idea of another account returns 404, like a missing one. | 204, 401, 404, 422 |

## health

Liveness and readiness for container healthchecks and Traefik.

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/health/live` | `healthLive` | Process is up | Answers as soon as the process accepts requests; does not touch the database. Target of the container healthcheck. | 200 |
| `GET /api/v1/health/ready` | `healthReady` | Database reachable | Runs `SELECT 1`. Without a database it returns `status: degraded` with HTTP 200, so that Traefik keeps the container in rotation while it is still starting. | 200 |

## occasions

Occasion types and occasions (F-03). The types Geburtstag and Weihnachten are system-wide and read-only; occasions are one-off or yearly and visible only to their account (Q-01).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/occasion-types` | `listOccasionTypes` | List occasion types | Returns the system-wide types Geburtstag and Weihnachten followed by the account's own types. System-wide types are read-only: there is no endpoint to change or delete them. | 200, 401, 422 |
| `GET /api/v1/occasion-types/{occasion_type_id}` | `getOccasionType` | Show occasion type | Returns one system-wide type or one of the account's own types. A type of another account returns 404. | 200, 401, 404, 422 |
| `GET /api/v1/occasions` | `listOccasions` | List occasions | Returns the occasions of the current account, sorted by date, one page at a time. `total` counts all occasions of the account. | 200, 401, 422 |
| `POST /api/v1/occasions` | `createOccasion` | Create occasion | Creates a one-off or yearly occasion for the current account. `occasion_type_id` must be a system-wide type or one of the account; otherwise 404. | 201, 401, 404, 422 |
| `GET /api/v1/occasions/{occasion_id}` | `getOccasion` | Show occasion | Returns one occasion of the current account. An occasion of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/occasions/{occasion_id}` | `updateOccasion` | Update occasion | Replaces all fields of the occasion: a field left out is reset to its default. An occasion of another account returns 404, like a missing one. `occasion_type_id` must be a system-wide type or one of the account; otherwise 404. | 200, 401, 404, 422 |
| `DELETE /api/v1/occasions/{occasion_id}` | `deleteOccasion` | Delete occasion | Deletes the occasion. Cannot be undone. An occasion of another account returns 404, like a missing one. | 204, 401, 404, 422 |

## people

People the account gives gifts to (F-02). Every account sees only its own people (Q-01).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/people` | `listPeople` | List people | Returns the people of the current account, sorted by name (case-insensitive), one page at a time. `total` counts all people of the account. | 200, 401, 422 |
| `POST /api/v1/people` | `createPerson` | Create person | Creates a person for the current account. Only the name is required; empty optional fields are stored as null. | 201, 401, 422 |
| `GET /api/v1/people/{person_id}` | `getPerson` | Show person | Returns one person of the current account. A person of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/people/{person_id}` | `updatePerson` | Update person | Replaces all fields of the person: a field left out is reset to null. The frontend sends the whole form. A person of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/people/{person_id}` | `deletePerson` | Delete person | Deletes the person. Cannot be undone. A person of another account returns 404, like a missing one. | 204, 401, 404, 422 |
