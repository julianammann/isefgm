import { env } from '$env/dynamic/private';
import type { RequestHandler } from './$types';

const API_URL = env.API_URL ?? 'http://localhost:8000';

const HOP_BY_HOP = [
  'connection',
  'content-length',
  'content-encoding',
  'host',
  'transfer-encoding'
];

const proxy: RequestHandler = async ({ request, params, url }) => {
  const target = new URL(`/api/${params.path}${url.search}`, API_URL);

  const headers = new Headers(request.headers);
  for (const h of HOP_BY_HOP) headers.delete(h);

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

export const GET = proxy;
export const POST = proxy;
export const PUT = proxy;
export const PATCH = proxy;
export const DELETE = proxy;
export const OPTIONS = proxy;
