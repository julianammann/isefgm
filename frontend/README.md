# Geschenke-Manager – Frontend

SvelteKit 2 mit Svelte 5 (Runes), TypeScript, Tailwind 4, `adapter-node`. Wird server-seitig gerendert und spricht das Backend ausschließlich same-origin an.

## Datenfluss

```
Browser ──▶ SvelteKit (Node, :3000) ──▶ FastAPI (:8000)
              │
              ├─ load / form actions: locals.api → event.fetch → hooks.server.ts:handleFetch → API_URL
              └─ Browser-Requests auf /api/* → routes/api/[...path]/+server.ts (Proxy) → API_URL
```

Regeln:

- Daten werden in `+page.server.ts` / `+layout.server.ts` über `load` geladen, mit `locals.api` (typisierter Client, an `event.fetch` gebunden).
- Schreibende Aktionen sind Form Actions. Sie funktionieren ohne JavaScript und per Tastatur (Q-07).
- Kein globaler API-Client. `createApiClient(event.fetch, event.url.origin)` immer mit dem request-gebundenen `fetch` und einer absoluten Basis-URL aufrufen; mit einer relativen wirft openapi-fetch auf dem Server.
- Fehler kommen vom Backend im Problem-Details-Format (`type`, `title`, `status`, `detail`, `errors[]`) und werden in `fail()` bzw. `error()` übersetzt; `problemMessage()` liefert den Text.
- **Doku:** Jede `.ts`-Datei unter `src/lib` und `src/routes` beginnt mit einem `@module`-Kommentar, jeder Export hat JSDoc (Englisch). TypeDoc bricht sonst ab. `.svelte`-Dateien liest TypeDoc nicht, Logik gehört deshalb in `.ts`.
- **Guard:** Geschützte Seiten liegen unter `(app)/`, Login und Registrierung unter `(auth)/`. Durchgesetzt wird das in `hooks.server.ts` über `guard()` (`lib/server/guard.ts`), nie in einem `+layout.server.ts`: Form Actions laufen ohne Layout-`load`, Seiten-`load`s parallel dazu. Neue geschützte Seiten brauchen nur den Ordner unter `(app)/`.
- **Backend-Ausfall:** Antwortet `/me` mit 5xx oder gar nicht, gilt der Anmeldestatus als unbekannt, nicht als abgemeldet. Der Hook beantwortet `(app)` dann für jede Methode mit 503, bevor ein `load` oder eine Action läuft; das Cookie bleibt erhalten. Die Seite ist `src/error.html`, weil ein Fehler aus `handle` nie `+error.svelte` erreicht; `__data.json` und `use:enhance` bekommen JSON. Der Statuspunkt im Kopf jeder Seite (`StatusDot`, Daten aus `routes/+layout.server.ts`) zeigt grün/gelb/rot für Backend und Datenbank, mit Text als Tooltip und für Screenreader.
- **Session:** Das Backend setzt das Cookie `session` auf seiner Antwort. Weil Actions serverseitig aufrufen, kopiert `forwardSessionCookie()` es auf die SvelteKit-Antwort. `hooks.server.ts` löst das Cookie pro Request über `/api/v1/auth/me` in `locals.user` auf.
- **Proxy:** Schreibende Requests (alles außer GET, HEAD, OPTIONS) auf `/api/*` nimmt der Hook nur an, wenn der `Origin`-Header der App-Origin entspricht, sonst 403. SvelteKits eigene Prüfung deckt nur Formular-Content-Types ab. Der Proxy leitet nur Pfade unter `/api/` weiter (`proxyTarget()`, sonst 404) und entfernt `Forwarded`, `X-Forwarded-*` und `X-Real-IP` des Browsers (`upstreamHeaders()`).
- **CSP:** `csp` in `vite.config.ts`. Skripte, Styles, Bilder, Fonts und Verbindungen nur von der eigenen Origin, SvelteKit versieht seine Inline-Skripte mit einer Nonce. Keine `style`-Attribute im Markup, Tailwind-Klassen stattdessen; einzige Ausnahme ist SvelteKits `#svelte-announcer`, für den `style-src-attr 'unsafe-inline'` gilt (ein Hash würde bei jedem SvelteKit-Update still brechen; Style-Attribute führen keinen Code aus).

## Struktur

```
src/
  hooks.server.ts         handleFetch (Backend-Weiterleitung), CSRF-Prüfung für /api, locals.api, locals.user, Route-Guard, Security-Header
  app.d.ts                App.Locals { api, user, authUnavailable }
  error.html              statische Fehlerseite für Fehler aus dem Hook (503 bei Backend-Ausfall)
  lib/api/client.ts       createApiClient(fetch, baseUrl), Typen User/Problem/Health, problemMessage()
  lib/api/schema.d.ts     generiert aus ../openapi.json, nie von Hand ändern
  lib/components/         StatusDot.svelte (Statuspunkt mit Tooltip)
  lib/health.ts           systemStatus(): Health-Antwort → grün/gelb/rot + Text
  lib/server/session.ts   Session-Cookie vom Backend auf die SvelteKit-Antwort übernehmen, safeNext()
  lib/server/guard.ts     guard(): (app) nur angemeldet, (auth) nur abgemeldet, 503 bei unbekanntem Status
  lib/server/csrf.ts      isCrossSiteApiWrite(): schreibende /api-Requests nur von der eigenen Origin
  lib/server/proxy.ts     proxyTarget(), upstreamHeaders(): Ziel-URL und Header für den Proxy
  routes/
    +layout.svelte        globales Layout, Tailwind
    +layout.server.ts     Systemstatus für den Statuspunkt
    +error.svelte         Fehlerseite für Fehler aus load und Actions
    (auth)/               nur abgemeldet; der Hook leitet eingeloggte Nutzer nach /; Kopf mit Statuspunkt
      login/, register/   Form Actions gegen /api/v1/auth/*
    (app)/                nur angemeldet; der Hook leitet ohne Session nach /login?next=…
      +page.svelte        Übersicht
      account/            Konto anzeigen, auf allen Geräten abmelden, Konto löschen (F-17)
    logout/               nur Action: Session widerrufen, Cookie löschen
    api/[...path]/        Proxy für Browser-Requests
```

## Kommandos

| Task        | Befehl                           | Zweck                                                |
| ----------- | -------------------------------- | ---------------------------------------------------- |
| `install`   | `pnpm install --frozen-lockfile` |                                                      |
| `dev`       | `pnpm run dev`                   | http://localhost:3000, Backend muss auf :8000 laufen |
| `lint`      | `pnpm run lint`                  | Prettier + ESLint                                    |
| `typecheck` | `pnpm run check`                 | svelte-check                                         |
| `test`      | `pnpm run test`                  | Vitest (Unit in Node, Komponenten in Chromium)       |
| `build`     | `pnpm run build`                 | Node-Build nach `build/`                             |
| `generate`  | `pnpm run generate`              | TypeScript-Typen aus `openapi.json`                  |
| `apidocs`   | `pnpm run docs`                  | Code-Referenz (TypeDoc) nach `../docs/site/frontend` |

Die Typen werden per Pre-Commit-Hook regeneriert, sobald sich Backend-Router oder -Schemas ändern. CI prüft in beide Richtungen: Backend-CI, dass `openapi.json` zum Code passt, Frontend-CI, dass `schema.d.ts` zu `openapi.json` passt.

## Konfiguration

| Variable  | Default                 | Bedeutung                                                                                                 |
| --------- | ----------------------- | --------------------------------------------------------------------------------------------------------- |
| `API_URL` | `http://localhost:8000` | Backend, das `handleFetch` und der Proxy ansprechen                                                       |
| `ORIGIN`  | –                       | Öffentliche Origin, nötig für Form Actions und schreibende `/api`-Requests in Produktion (`adapter-node`) |

## Docker

```sh
docker build -t giftmanager-frontend .
```

Multi-Stage: Build mit pnpm, Laufzeit `node:26-alpine`, Non-Root-User, Port 3000.
