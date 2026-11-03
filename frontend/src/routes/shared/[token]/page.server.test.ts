import { describe, expect, it, vi } from 'vitest';

import { load } from './+page.server.ts';

type LoadEvent = Parameters<typeof load>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const status = (code: number) => ({ response: new Response(null, { status: code }) });

function loadEvent(response: unknown) {
  const GET = vi.fn().mockResolvedValue(response);
  return {
    event: { locals: { api: { GET } }, params: { token: 'tok' } } as unknown as LoadEvent,
    GET
  };
}

const shared = {
  owner_name: 'Anna',
  expires_at: '2026-12-24T22:59:59Z',
  people: [{ name: 'Lena', gifts: [] }]
};

describe('load', () => {
  it('opens the list behind the token and gives the expiry day in German time', async () => {
    const { event, GET } = loadEvent(ok(shared));
    await expect(load(event)).resolves.toEqual({ shared, expires_on: '2026-12-24' });
    expect(GET).toHaveBeenCalledWith('/api/v1/shared/{token}', {
      params: { path: { token: 'tok' } }
    });
  });

  it('answers every link that does not open with the same 404', async () => {
    for (const code of [404, 422]) {
      await expect(load(loadEvent(status(code)).event)).rejects.toMatchObject({
        status: 404,
        body: { message: 'Dieser Link ist nicht gültig oder nicht mehr aktiv.' }
      });
    }
  });
});
