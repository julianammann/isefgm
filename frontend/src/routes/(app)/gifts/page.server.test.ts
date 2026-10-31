import { describe, expect, it, vi } from 'vitest';

import { actions, load } from './+page.server.ts';

type LoadEvent = Parameters<typeof load>[0];
type ActionEvent = Parameters<typeof actions.create>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const empty = ok({ items: [], total: 0 });

/** Load event whose gift list answers with `total`; other lists are empty. */
function loadEvent(search: string, total: number, items: unknown[] = []) {
  const GET = vi.fn(async (path: string) =>
    path === '/api/v1/gifts' ? ok({ items, total }) : empty
  );
  const event = {
    locals: { api: { GET } },
    url: new URL(`http://localhost/gifts${search}`)
  } as unknown as LoadEvent;
  return { event, GET };
}

function giftCalls(GET: ReturnType<typeof vi.fn>) {
  return GET.mock.calls.filter(([path]) => path === '/api/v1/gifts');
}

describe('load', () => {
  it('requests the page from the backend and returns page and total', async () => {
    const { event, GET } = loadEvent('?page=2', 450);
    const data = (await load(event)) as { page: number; total: number };
    expect(giftCalls(GET)[0][1].params.query).toEqual({ limit: 200, offset: 200 });
    expect(data).toMatchObject({ page: 2, total: 450 });
  });

  it('redirects a page beyond the last one, keeping other params', async () => {
    const { event } = loadEvent('?page=5&success=deleted', 450);
    await expect(load(event)).rejects.toMatchObject({
      status: 303,
      location: '/gifts?page=3&success=deleted'
    });
  });

  it('treats an invalid page as page 1 without redirect', async () => {
    const { event, GET } = loadEvent('?page=abc', 10);
    await expect(load(event)).resolves.toMatchObject({ page: 1 });
    expect(giftCalls(GET)[0][1].params.query.offset).toBe(0);
  });

  it('shows the empty list without redirect when there are no entries', async () => {
    const { event } = loadEvent('?page=3', 0);
    await expect(load(event)).resolves.toMatchObject({ page: 3, total: 0, gifts: [] });
  });

  it('finds the idea to edit in the page items', async () => {
    const gift = { id: 'g1', title: 'Buch', category: 'other', people: [], occasions: [] };
    const { event } = loadEvent('?edit=g1', 1, [gift]);
    const data = (await load(event)) as { editing: { id: string } | null };
    expect(data.editing?.id).toBe('g1');
  });
});

/** Action event posting a valid form to `?<search>`. */
function actionEvent(search: string, api: Record<string, unknown>) {
  const body = new FormData();
  body.set('id', 'g1');
  body.set('title', 'Buch');
  return {
    request: new Request(`http://localhost/gifts${search}`, { method: 'POST', body }),
    url: new URL(`http://localhost/gifts${search}`),
    locals: { api }
  } as unknown as ActionEvent;
}

const success = { response: new Response(null, { status: 200 }), data: { id: 'g1' } };

describe('actions', () => {
  it('create redirects to page 1 even when posted from another page', async () => {
    const api = { POST: vi.fn().mockResolvedValue(success) };
    await expect(actions.create(actionEvent('?page=3', api))).rejects.toMatchObject({
      status: 303,
      location: '/gifts?success=created'
    });
  });

  it('update stays on the posted page', async () => {
    const api = { PUT: vi.fn().mockResolvedValue(success) };
    await expect(actions.update(actionEvent('?page=3', api))).rejects.toMatchObject({
      status: 303,
      location: '/gifts?page=3&success=updated'
    });
  });

  it('delete stays on the posted page', async () => {
    const api = {
      DELETE: vi.fn().mockResolvedValue({ response: new Response(null, { status: 204 }) })
    };
    await expect(actions.delete(actionEvent('?page=3', api))).rejects.toMatchObject({
      status: 303,
      location: '/gifts?page=3&success=deleted'
    });
  });
});
