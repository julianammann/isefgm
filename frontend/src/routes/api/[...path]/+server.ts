/**
 * Public proxy `/api/*` -> backend, for calls made from the browser.
 * Server-side code does not come through here: `handleFetch` in `hooks.server.ts`
 * sends those requests to the backend directly.
 *
 * @module
 */
import { env } from '$env/dynamic/private';
import { json } from '@sveltejs/kit';
import type { RequestHandler } from './$types';

import { HOP_BY_HOP, proxyTarget, upstreamHeaders } from '$lib/server/proxy';

const API_URL = env.API_URL ?? 'http://localhost:8000';

const proxy: RequestHandler = async ({ request, params, url }) => {
  const target = proxyTarget(params.path, url.search, API_URL);
  if (!target) {
    // Outside /api/ on the backend: answer like a backend 404 without asking it.
    return json({ title: 'Not Found', status: 404, detail: 'Not Found' }, { status: 404 });
  }

  const headers = upstreamHeaders(request.headers);

  const hasBody = !['GET', 'HEAD'].includes(request.method);
  const upstream = await fetch(target, {
    method: request.method,
    headers,
    body: hasBody ? await request.arrayBuffer() : undefined
  });

  const responseHeaders = new Headers(upstream.headers);
  for (const h of HOP_BY_HOP) responseHeaders.delete(h);

  return new Response(upstream.body, { status: upstream.status, headers: responseHeaders });
};

/** Forwards `GET /api/*` to the backend. */
export const GET = proxy;
/** Forwards `POST /api/*` to the backend. */
export const POST = proxy;
/** Forwards `PUT /api/*` to the backend. */
export const PUT = proxy;
/** Forwards `PATCH /api/*` to the backend. */
export const PATCH = proxy;
/** Forwards `DELETE /api/*` to the backend. */
export const DELETE = proxy;
/** Forwards `OPTIONS /api/*` to the backend. */
export const OPTIONS = proxy;
