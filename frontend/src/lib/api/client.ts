import createClient from 'openapi-fetch';

import type { paths } from './schema';

export type ApiClient = ReturnType<typeof createClient<paths>>;

export function createApiClient(fetchFn: typeof fetch = fetch, baseUrl = ''): ApiClient {
  return createClient<paths>({ baseUrl, fetch: fetchFn });
}

export const api = createApiClient();
