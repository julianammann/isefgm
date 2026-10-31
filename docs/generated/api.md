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

## full-list

The complete list of the account's people, gift ideas and past gifts in one response (F-15). Visible only to its account (Q-01).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/full-list` | `getFullList` | Show complete list | Returns all people, all gift ideas with their links and notes, and all past gifts (giftings with status `given`) of the current account in one response. The frontend renders it as one HTML page. Not paginated on purpose: F-15 asks for the complete list; all rows are loaded in a fixed number of queries. | 200, 401 |

## giftings



| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/giftings` | `listGiftings` | List giftings | Returns the giftings of the current account, newest first, one page at a time. `total` counts all giftings of the account. | 200, 401, 422 |
| `POST /api/v1/giftings` | `createGifting` | Create gifting | Turns a gift idea into a gifting in one step: only `gift_id` is required, the status defaults to `idea`. The idea is referenced, not copied, and stays in the idea list. A past gift is recorded directly with status `given`. A gifting at the occasion Geburtstag needs exactly one recipient, otherwise 422. Status `given` needs at least one recipient, `occasion_id`, `occasion_date` and `given_on` (422 otherwise); `given_on` is not stored with any other status. `gift_id`, `person_ids` and `occasion_id` must belong to the account; an ID of another account returns 404, like a missing one, and nothing is saved. | 201, 401, 404, 422 |
| `GET /api/v1/giftings/{gifting_id}` | `getGifting` | Show gifting | Returns one gifting of the current account. A gifting of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/giftings/{gifting_id}` | `updateGifting` | Update gifting | Replaces all fields of the gifting, including its recipients: a field left out is reset to null, its default or an empty list. Any status may follow any other. A gifting at the occasion Geburtstag needs exactly one recipient, otherwise 422. Status `given` needs at least one recipient, `occasion_id`, `occasion_date` and `given_on` (422 otherwise); `given_on` is not stored with any other status. `gift_id`, `person_ids` and `occasion_id` must belong to the account; an ID of another account returns 404, like a missing one, and nothing is saved. A gifting of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/giftings/{gifting_id}` | `deleteGifting` | Delete gifting | Deletes the gifting together with its tasks. The idea, the people and the occasion stay. Cannot be undone. A gifting of another account returns 404, like a missing one. | 204, 401, 404, 422 |

## gifts



| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/gifts` | `listGifts` | List gift ideas | Returns the gift ideas of the current account, newest first, one page at a time. `total` counts all gift ideas of the account. | 200, 401, 422 |
| `POST /api/v1/gifts` | `createGift` | Create gift idea | Creates a gift idea for the current account. Only the title is required, so an idea can be captured in one step: empty optional fields are stored as null and `category` defaults to `other`. `currency` is stored only with a price, EUR if none is given. The creation time is set by the server. `person_ids` and `occasion_ids` link the idea to people and occasions of the account; an ID of another account returns 404, like a missing one, and nothing is saved. | 201, 401, 404, 422 |
| `GET /api/v1/gifts/{gift_id}` | `getGift` | Show gift idea | Returns one gift idea of the current account. A gift idea of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/gifts/{gift_id}` | `updateGift` | Update gift idea | Replaces all fields of the gift idea, including its links: a field left out is reset to null, its default or an empty list. The frontend sends the whole form. `person_ids` and `occasion_ids` link the idea to people and occasions of the account; an ID of another account returns 404, like a missing one, and nothing is saved. A gift idea of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/gifts/{gift_id}` | `deleteGift` | Delete gift idea | Deletes the gift idea with its notes, links and images. Cannot be undone. A gift idea of another account returns 404, like a missing one. A gift idea used by a gifting cannot be deleted; this returns 409. | 204, 401, 404, 409, 422 |

## health

Liveness and readiness for container healthchecks and Traefik.

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/health/live` | `healthLive` | Process is up | Answers as soon as the process accepts requests; does not touch the database. Target of the container healthcheck. | 200 |
| `GET /api/v1/health/ready` | `healthReady` | Database reachable | Runs `SELECT 1`. Without a database it returns `status: degraded` with HTTP 200, so that Traefik keeps the container in rotation while it is still starting. | 200 |

## images

Labelled images on gift ideas (F-07): JPEG, PNG or WebP up to 5 MB, stored as WebP without metadata, at most 5 per idea. Files are served only to the owner's session or through a valid share link (Q-01, Q-03).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/images` | `listImages` | List images | Returns the images of the current account, oldest first, one page at a time. `gift_id` narrows the list to one idea; an idea of another account gives an empty page. | 200, 401, 422 |
| `POST /api/v1/images` | `createImage` | Upload image | Adds a labelled image to a gift idea of the current account. Accepts JPEG, PNG and WebP up to 5 MB, judged by the content, not by the file name or type (415 for anything else). Larger files, or more than 24 megapixels for JPEG, 16 for PNG and 10 for WebP, return 413. The image is turned upright, shrunk to at most 2000 px on its long side and stored as WebP without EXIF or XMP metadata. An idea holds at most 5 images (409). While too many uploads are in progress the API answers 503 with Retry-After. `gift_id` must be a gift idea of the account; an idea of another account returns 404, like a missing one, and nothing is saved. | 201, 401, 404, 409, 413, 415, 422, 503 |
| `GET /api/v1/images/{image_id}` | `getImage` | Show image | Returns the details of one image of the current account; the file itself comes from `/images/{image_id}/content`. An image of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/images/{image_id}` | `updateImage` | Update image label | Replaces the label of the image. The file and the gift idea cannot be changed; upload a new image instead. An image of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/images/{image_id}` | `deleteImage` | Delete image | Deletes the image and its file. Cannot be undone. An image of another account returns 404, like a missing one. | 204, 401, 404, 422 |
| `GET /api/v1/images/{image_id}/content` | `getImageContent` | Fetch image file | Returns the stored WebP file of one image of the current account, marked `Cache-Control: private, no-store`. An image of another account returns 404, like a missing one. | 200, 401, 404, 422 |

## links



| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/links` | `listLinks` | List links | Returns the links of the current account, oldest first, one page at a time. `gift_id` narrows the list to one idea; an idea of another account gives an empty page. | 200, 401, 422 |
| `POST /api/v1/links` | `createLink` | Create link | Adds a labelled link to a gift idea of the current account. The URL is stored as entered. `gift_id` must be a gift idea of the account; an idea of another account returns 404, like a missing one, and nothing is saved. `url` must be an absolute http or https URL (422 otherwise). | 201, 401, 404, 422 |
| `GET /api/v1/links/{link_id}` | `getLink` | Show link | Returns one link of the current account. A link of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/links/{link_id}` | `updateLink` | Update link | Replaces all fields of the link. `gift_id` must be a gift idea of the account; an idea of another account returns 404, like a missing one, and nothing is saved. `url` must be an absolute http or https URL (422 otherwise). A link of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/links/{link_id}` | `deleteLink` | Delete link | Deletes the link. Cannot be undone. A link of another account returns 404, like a missing one. | 204, 401, 404, 422 |

## notes



| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/notes` | `listNotes` | List notes | Returns the notes of the current account, oldest first, one page at a time. `gift_id` narrows the list to one idea; an idea of another account gives an empty page. | 200, 401, 422 |
| `POST /api/v1/notes` | `createNote` | Create note | Adds a labelled note to a gift idea of the current account. `gift_id` must be a gift idea of the account; an idea of another account returns 404, like a missing one, and nothing is saved. | 201, 401, 404, 422 |
| `GET /api/v1/notes/{note_id}` | `getNote` | Show note | Returns one note of the current account. A note of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/notes/{note_id}` | `updateNote` | Update note | Replaces all fields of the note. `gift_id` must be a gift idea of the account; an idea of another account returns 404, like a missing one, and nothing is saved. A note of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/notes/{note_id}` | `deleteNote` | Delete note | Deletes the note. Cannot be undone. A note of another account returns 404, like a missing one. | 204, 401, 404, 422 |

## occasions

Occasion types and occasions (F-03). The types Geburtstag, Weihnachten and Ostern are system-wide and read-only; occasions are one-off or yearly and visible only to their account (Q-01). Geburtstag, Weihnachten and Ostern also exist once per account as rule occasions, which are read-only.

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/occasion-types` | `listOccasionTypes` | List occasion types | Returns the system-wide types Geburtstag, Weihnachten and Ostern followed by the account's own types. System-wide types are read-only: there is no endpoint to change or delete them. | 200, 401, 422 |
| `GET /api/v1/occasion-types/{occasion_type_id}` | `getOccasionType` | Show occasion type | Returns one system-wide type or one of the account's own types. A type of another account returns 404. | 200, 401, 404, 422 |
| `GET /api/v1/occasions` | `listOccasions` | List occasions | Returns the occasions of the current account, one page at a time: the rule occasions Geburtstag, Weihnachten and Ostern first, then the others sorted by month and day (the year is ignored). `total` counts all occasions of the account. | 200, 401, 422 |
| `POST /api/v1/occasions` | `createOccasion` | Create occasion | Creates a one-off or yearly occasion for the current account. `occasion_type_id` must be a system-wide type or one of the account; otherwise 404. Geburtstag, Weihnachten and Ostern return 422: rule occasions exist once per account. `person_ids` links the occasion to people of the account; an ID of another account returns 404, like a missing one, and nothing is saved. | 201, 401, 404, 422 |
| `GET /api/v1/occasions/{occasion_id}` | `getOccasion` | Show occasion | Returns one occasion of the current account. An occasion of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/occasions/{occasion_id}` | `updateOccasion` | Update occasion | Replaces all fields of the occasion, including its links: a field left out is reset to its default or an empty list. The frontend sends the whole form. An occasion of another account returns 404, like a missing one. `occasion_type_id` must be a system-wide type or one of the account; otherwise 404. Geburtstag, Weihnachten and Ostern return 422: rule occasions exist once per account. `person_ids` links the occasion to people of the account; an ID of another account returns 404, like a missing one, and nothing is saved. A rule occasion (Geburtstag, Weihnachten, Ostern) cannot be changed or deleted; this returns 409. | 200, 401, 404, 409, 422 |
| `DELETE /api/v1/occasions/{occasion_id}` | `deleteOccasion` | Delete occasion | Deletes the occasion. Cannot be undone. An occasion of another account returns 404, like a missing one. A rule occasion (Geburtstag, Weihnachten, Ostern) cannot be changed or deleted; this returns 409. An occasion used by a gifting cannot be deleted; this returns 409. | 204, 401, 404, 409, 422 |

## people

People the account gives gifts to (F-02). Every account sees only its own people (Q-01).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/people` | `listPeople` | List people | Returns the people of the current account, sorted by name (case-insensitive), one page at a time. `total` counts all people of the account. | 200, 401, 422 |
| `POST /api/v1/people` | `createPerson` | Create person | Creates a person for the current account. Only the name is required; empty optional fields are stored as null. Through `birthday` the person belongs to the account's rule occasion Geburtstag. | 201, 401, 422 |
| `GET /api/v1/people/{person_id}` | `getPerson` | Show person | Returns one person of the current account. A person of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/people/{person_id}` | `updatePerson` | Update person | Replaces all fields of the person: a field left out is reset to null. The frontend sends the whole form. Through `birthday` the person belongs to the account's rule occasion Geburtstag. A person of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/people/{person_id}` | `deletePerson` | Delete person | Deletes the person. Cannot be undone. A person of another account returns 404, like a missing one. | 204, 401, 404, 422 |
| `GET /api/v1/people/{person_id}/overview` | `getPersonOverview` | Show person view | Returns what the person view shows (F-09): past gifts (`given`) and the giftings not given yet with their procurement state (`giftings`), both with occasion and tasks, the gift ideas meant for the person and not used for them yet (`ideas`) and the occasions that concern them (`occasions`). Every list is one page with the same `limit` and `offset` and its own `total`; all rows are loaded in a fixed number of queries. A person of another account returns 404, like a missing one. | 200, 401, 404, 422 |

## share-links

Read-only share links on chosen people (F-14). The token is shown once on creation and stored only as a hash; a link can expire and be deactivated at any time (Q-03).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/share-links` | `listShareLinks` | List share links | Returns the share links of the current account, newest first, one page at a time. Tokens are not included; they are shown only once, on creation. | 200, 401, 422 |
| `POST /api/v1/share-links` | `createShareLink` | Create share link | Creates a read-only share link on chosen people of the current account. The response holds the token, the only time it is returned: the server keeps just its SHA-256 hash. `person_ids` must name 1 to 100 people of the account; a person of another account returns 404, like a missing one, and nothing is saved. An `expires_at` that is set or changed must lie in the future (400 otherwise). | 201, 400, 401, 404, 422 |
| `GET /api/v1/share-links/{share_link_id}` | `getShareLink` | Show share link | Returns one share link of the current account, without its token. A share link of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/share-links/{share_link_id}` | `updateShareLink` | Update share link | Replaces the people, expiry time and active flag of the share link. `active: false` deactivates it at once; the token stays the same. `person_ids` must name 1 to 100 people of the account; a person of another account returns 404, like a missing one, and nothing is saved. An `expires_at` that is set or changed must lie in the future (400 otherwise). A share link of another account returns 404, like a missing one. | 200, 400, 401, 404, 422 |
| `DELETE /api/v1/share-links/{share_link_id}` | `deleteShareLink` | Delete share link | Deletes the share link; it no longer opens. Cannot be undone. A share link of another account returns 404, like a missing one. | 204, 401, 404, 422 |

## shared

Public view behind a valid share link, no login needed (F-14). Shows only the chosen people by name and their gift ideas with web links and images; nothing can be changed (Q-01).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/shared/{token}` | `getSharedList` | Open shared list | Public, read-only view behind a share link, no login needed. Returns the chosen people with only their names and the gift ideas meant for them, with web links and images. An unknown, deactivated or expired token returns the same 404, so the response does not tell them apart. Other methods return 405. | 200, 404, 422 |
| `GET /api/v1/shared/{token}/images/{image_id}` | `getSharedImage` | Fetch shared image file | Public, no login needed: returns the WebP file of an image on one of the gift ideas the share link shows, marked `Cache-Control: private, no-store`. An unknown, deactivated or expired token, or an image the link does not show, returns the same 404 as the shared list. | 200, 404, 422 |

## suggestions

Gift suggestions for a person (F-16): category and price band shared by the gift ideas of several other accounts, without titles, texts or people of other accounts (Q-04). Visible only to their account (Q-01).

| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `POST /api/v1/suggestions` | `createSuggestions` | Make suggestions | Replaces the open suggestions for a person of the current account with up to 5 new ones, most frequent first. Each is a category and price band shared by gift ideas of at least 3 other accounts; the account's own ideas do not count, and no title or text of another account is used (Q-04). Features the person already has as an idea or gifting, and features accepted or dismissed for them before, are left out. The list may be empty. A person of another account returns 404, like a missing one. | 201, 401, 404, 422 |
| `GET /api/v1/suggestions` | `listSuggestions` | List suggestions | Returns the open suggestions of the current account, one page at a time, most frequent first. `person_id` narrows the list to one person; a person of another account gives an empty page. | 200, 401, 422 |
| `GET /api/v1/suggestions/{suggestion_id}` | `getSuggestion` | Show suggestion | Returns one suggestion of the current account in any status. A suggestion of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `POST /api/v1/suggestions/{suggestion_id}/accept` | `acceptSuggestion` | Accept suggestion | Creates a gift idea for the suggestion's person with the given title, the suggested category and the price range of the band in EUR, and marks the suggestion `accepted`. Returns the new gift idea. Only an open suggestion can be accepted or dismissed; otherwise 409. A suggestion of another account returns 404, like a missing one. | 201, 401, 404, 409, 422 |
| `POST /api/v1/suggestions/{suggestion_id}/dismiss` | `dismissSuggestion` | Dismiss suggestion | Marks the suggestion `dismissed`. Its category and price band are never suggested for the person again. Only an open suggestion can be accepted or dismissed; otherwise 409. A suggestion of another account returns 404, like a missing one. | 200, 401, 404, 409, 422 |

## tasks



| Endpoint | operationId | Purpose | Behaviour | Status |
| --- | --- | --- | --- | --- |
| `GET /api/v1/tasks` | `listTasks` | List tasks | Returns the tasks of the current account, one page at a time: earliest due date first, tasks without one last, the same due date in creation order. `gifting_id` narrows the list to one gifting; a gifting of another account gives an empty page. | 200, 401, 422 |
| `POST /api/v1/tasks` | `createTask` | Create task | Adds a task to a gifting of the current account. `gifting_id` must be a gifting of the account, in any status from `idea` on; a gifting of another account returns 404, like a missing one, and nothing is saved. | 201, 401, 404, 422 |
| `GET /api/v1/tasks/{task_id}` | `getTask` | Show task | Returns one task of the current account. A task of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `PUT /api/v1/tasks/{task_id}` | `updateTask` | Update task | Replaces all fields of the task; a left-out `due_on` removes the due date. `gifting_id` must be a gifting of the account, in any status from `idea` on; a gifting of another account returns 404, like a missing one, and nothing is saved. A task of another account returns 404, like a missing one. | 200, 401, 404, 422 |
| `DELETE /api/v1/tasks/{task_id}` | `deleteTask` | Delete task | Deletes the task. Cannot be undone. A task of another account returns 404, like a missing one. | 204, 401, 404, 422 |
