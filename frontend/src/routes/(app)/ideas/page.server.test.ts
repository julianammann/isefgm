import { describe, expect, it, vi } from 'vitest';

import { actions, load } from './+page.server.ts';

type LoadEvent = Parameters<typeof load>[0];
type ActionEvent = Parameters<typeof actions.adopt>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });

function loadEvent(search: string, total: number, items: string[] = []) {
  const GET = vi.fn(async () => ok({ items, total }));
  const event = {
    locals: { api: { GET } },
    url: new URL(`http://localhost/ideas${search}`)
  } as unknown as LoadEvent;
  return { event, GET };
}

describe('load', () => {
  it('requests the page of titles and returns titles, page and total', async () => {
    const { event, GET } = loadEvent('?page=2', 450, ['Kochbuch']);
    const data = await load(event);
    expect(GET).toHaveBeenCalledWith('/api/v1/suggestions/titles', {
      params: { query: { limit: 200, offset: 200 } }
    });
    expect(data).toMatchObject({ page: 2, total: 450, titles: ['Kochbuch'], success: null });
  });

  it('redirects a page beyond the last one', async () => {
    const { event } = loadEvent('?page=5', 450);
    await expect(load(event)).rejects.toMatchObject({ status: 303, location: '/ideas?page=3' });
  });

  it('shows the message after adopting a title', async () => {
    const { event } = loadEvent('?success=adopted', 1, ['Kochbuch']);
    await expect(load(event)).resolves.toMatchObject({
      success: 'Als Geschenkidee übernommen!'
    });
  });
});

function adoptEvent(title: string, api: Record<string, unknown>) {
  const body = new FormData();
  body.set('title', title);
  return {
    request: new Request('http://localhost/ideas?page=2&/adopt', { method: 'POST', body }),
    url: new URL('http://localhost/ideas?page=2&/adopt'),
    locals: { api }
  } as unknown as ActionEvent;
}

describe('adopt', () => {
  it('creates a gift idea with only the title and stays on the page', async () => {
    const POST = vi.fn().mockResolvedValue(ok({ id: 'g1' }));
    await expect(actions.adopt(adoptEvent('Kochbuch', { POST }))).rejects.toMatchObject({
      status: 303,
      location: '/ideas?page=2&success=adopted'
    });
    expect(POST).toHaveBeenCalledWith('/api/v1/gifts', {
      body: { title: 'Kochbuch', category: 'other' }
    });
  });

  it('returns the message when the backend refuses', async () => {
    const POST = vi.fn().mockResolvedValue({ response: new Response(null, { status: 422 }) });
    await expect(actions.adopt(adoptEvent('', { POST }))).resolves.toMatchObject({
      status: 422,
      data: { message: 'Die Eingaben sind ungültig.' }
    });
  });
});
