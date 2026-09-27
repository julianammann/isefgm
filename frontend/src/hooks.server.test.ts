import type { Cookies, RequestEvent } from '@sveltejs/kit';
import { describe, expect, it, vi } from 'vitest';

import type { User } from '$lib/api/client';
import { SERVICE_UNAVAILABLE } from '$lib/server/guard';

import { handle } from './hooks.server.ts';

const ORIGIN = 'http://app.test';
const PROXY = '/api/[...path]';

const anna: User = {
  id: '0190c6f4-0000-7000-8000-000000000000',
  email: 'anna@example.org',
  display_name: 'Anna',
  created_at: '2026-09-27T12:00:00Z'
};

/** The parts of a `RequestEvent` that `handle` reads or writes. */
type HookEvent = Pick<RequestEvent, 'cookies' | 'fetch' | 'locals' | 'request' | 'route' | 'url'>;

interface FakeRequest {
  method: string;
  /** Path and query as the browser sent them. */
  path: string;
  /** `event.route.id`, i.e. the route SvelteKit matched on the decoded path. */
  routeId: RequestEvent['route']['id'];
  /** `Origin` header; `null` leaves it out. */
  origin: string | null;
  /** Whether the browser sends a session cookie. */
  session?: boolean;
  /** Stands in for the backend behind `event.fetch`. */
  backend?: typeof fetch;
}

/** Backend that answers every call with `status` and a JSON `body`. */
function answering(status: number, body: unknown = {}): typeof fetch {
  return async () => Response.json(body, { status });
}

/** Backend that cannot be reached. */
const unreachable: typeof fetch = async () => {
  throw new TypeError('fetch failed');
};

/** Request event for `handle` plus a spy standing in for the rest of SvelteKit. */
function fakeEvent({
  method,
  path,
  routeId,
  origin,
  session = false,
  backend = unreachable
}: FakeRequest) {
  const url = new URL(path, ORIGIN);
  const jar: Record<string, string> = session ? { '__Host-session': 'token' } : {};
  const cookies: Cookies = {
    get: (name) => jar[name],
    getAll: () => Object.entries(jar).map(([name, value]) => ({ name, value })),
    set: vi.fn(),
    delete: vi.fn(),
    serialize: vi.fn()
  };
  const event: HookEvent = {
    request: new Request(url, { method, headers: origin === null ? {} : { origin } }),
    url,
    route: { id: routeId },
    cookies,
    locals: {} as App.Locals, // filled in by handle
    fetch: backend
  };
  const resolve = vi.fn(async () => new Response('page'));
  return { event, resolve };
}

/** Runs `handle`; a thrown `error()` or `redirect()` becomes a rejection. */
async function run({ event, resolve }: ReturnType<typeof fakeEvent>): Promise<Response> {
  return handle({ event: event as RequestEvent, resolve });
}

describe('handle: CSRF check on the /api proxy', () => {
  it('rejects a cross-site POST with 403 before the proxy runs', async () => {
    for (const origin of ['https://evil.example', null]) {
      const fake = fakeEvent({
        method: 'POST',
        path: '/api/v1/auth/logout',
        routeId: PROXY,
        origin
      });
      expect((await run(fake)).status).toBe(403);
      expect(fake.resolve).not.toHaveBeenCalled();
    }
  });

  it('keys on the matched route, not the raw path: /%61pi/... is rejected too', async () => {
    const fake = fakeEvent({
      method: 'POST',
      path: '/%61pi/v1/auth/logout',
      routeId: PROXY,
      origin: 'https://evil.example'
    });
    // SvelteKit matched the decoded path; event.url keeps the encoding.
    expect(fake.event.url.pathname).toBe('/%61pi/v1/auth/logout');
    expect((await run(fake)).status).toBe(403);
    expect(fake.resolve).not.toHaveBeenCalled();
  });

  it('lets a same-origin POST through to the proxy', async () => {
    const fake = fakeEvent({
      method: 'POST',
      path: '/api/v1/auth/logout',
      routeId: PROXY,
      origin: ORIGIN
    });
    expect((await run(fake)).status).toBe(200);
    expect(fake.resolve).toHaveBeenCalledOnce();
  });
});

describe('handle: route guard', () => {
  it('answers (app) with 503 for every method when the backend cannot tell who is logged in', async () => {
    for (const backend of [answering(500, { title: 'Internal Server Error' }), unreachable]) {
      for (const [method, path] of [
        ['GET', '/account'],
        ['POST', '/account?/logoutAll']
      ]) {
        const fake = fakeEvent({
          method,
          path,
          routeId: '/(app)/account',
          origin: ORIGIN,
          session: true,
          backend
        });
        await expect(run(fake)).rejects.toMatchObject({
          status: 503,
          body: { message: SERVICE_UNAVAILABLE }
        });
        expect(fake.resolve).not.toHaveBeenCalled();
      }
    }
  });

  it('sends anonymous users from (app) to the login', async () => {
    const fake = fakeEvent({
      method: 'GET',
      path: '/account',
      routeId: '/(app)/account',
      origin: null
    });
    await expect(run(fake)).rejects.toMatchObject({
      status: 303,
      location: '/login?next=%2Faccount'
    });
    expect(fake.resolve).not.toHaveBeenCalled();
  });

  it('renders (app) for a logged-in user and adds the security headers', async () => {
    const fake = fakeEvent({
      method: 'GET',
      path: '/account',
      routeId: '/(app)/account',
      origin: null,
      session: true,
      backend: answering(200, anna)
    });
    const response = await run(fake);
    expect(fake.resolve).toHaveBeenCalledExactlyOnceWith(fake.event);
    expect(fake.event.locals.user).toEqual(anna);
    expect(response.headers.get('X-Content-Type-Options')).toBe('nosniff');
    expect(response.headers.get('Referrer-Policy')).toBe('strict-origin-when-cross-origin');
    expect(response.headers.get('X-Frame-Options')).toBe('DENY');
  });
});
