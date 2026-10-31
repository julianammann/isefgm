import { describe, expect, it, vi } from 'vitest';

import { actions, load } from './+page.server.ts';

type LoadEvent = Parameters<typeof load>[0];
type ActionEvent = Parameters<typeof actions.delete>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const page = (items: unknown[]) => ok({ items, total: items.length });
const status = (code: number) => ({ response: new Response(null, { status: code }) });

const gift = { id: 'g1', title: 'Buch', people: [], occasions: [] };

/** Load event whose backend answers GET by path; lists without an entry are empty. */
function loadEvent(responses: Record<string, unknown>) {
  const GET = vi.fn(async (path: string) => responses[path] ?? page([]));
  return {
    locals: { api: { GET } },
    params: { id: 'g1' },
    url: new URL('http://localhost/gifts/g1')
  } as unknown as LoadEvent;
}

describe('load', () => {
  it('answers 404 for an unknown idea', async () => {
    const event = loadEvent({ '/api/v1/gifts/{gift_id}': status(404) });
    await expect(load(event)).rejects.toMatchObject({ status: 404 });
  });

  it('keeps only the giftings of this idea', async () => {
    const event = loadEvent({
      '/api/v1/gifts/{gift_id}': ok(gift),
      '/api/v1/giftings': page([
        { id: 'own', gift: { id: 'g1' } },
        { id: 'foreign', gift: { id: 'g2' } }
      ])
    });
    const data = (await load(event)) as { giftings: unknown[] };
    expect(data.giftings.length).toBe(1);
  });
});

describe('delete', () => {
  it('reports a gifting that still uses the idea', async () => {
    const DELETE = vi.fn().mockResolvedValue(status(409));
    const event = { locals: { api: { DELETE } }, params: { id: 'g1' } } as unknown as ActionEvent;
    await expect(actions.delete(event)).resolves.toMatchObject({
      status: 409,
      data: {
        scope: 'delete',
        message:
          'Die Idee wird von mindestens einer Beschenkung verwendet und kann nicht gelöscht werden.'
      }
    });
  });
});
