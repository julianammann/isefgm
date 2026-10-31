import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import { createTaskForGift, parseTaskForm } from './tasks';

function createApi(handler: (request: Request) => Promise<Response>) {
  const requests: { method: string; path: string; body: unknown }[] = [];
  const fetchFn: typeof fetch = async (input, init) => {
    const request = input instanceof Request ? input : new Request(input, init);
    const raw = await request.clone().text();
    requests.push({
      method: request.method,
      path: new URL(request.url).pathname,
      body: raw ? JSON.parse(raw) : undefined
    });
    return handler(request);
  };
  return { api: createApiClient(fetchFn, 'http://api.test'), requests };
}

const json = (body: unknown, status = 200) =>
  new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } });

const gift = { id: 'gift1', people: [{ id: 'p1' }] };
const task = { title: 'Buy it', status: 'open' as const, due_on: null };

describe('createTaskForGift', () => {
  it("creates an idea gifting with the gift's people", async () => {
    const { api, requests } = createApi((r) =>
      Promise.resolve(
        new URL(r.url).pathname === '/api/v1/giftings'
          ? json({ id: 'g-new' }, 201)
          : json({ id: 't1', gifting_id: 'g-new' }, 201)
      )
    );
    const result = await createTaskForGift(api, gift, task);
    expect(result.ok).toBe(true);
    expect(requests[0]).toEqual({
      method: 'POST',
      path: '/api/v1/giftings',
      body: {
        gift_id: 'gift1',
        person_ids: ['p1'],
        status: 'idea',
        occasion_id: null,
        occasion_date: null,
        given_on: null
      }
    });
    expect(requests[1].path).toBe('/api/v1/tasks');
    expect(requests[1].body).toMatchObject({ gifting_id: 'g-new', title: 'Buy it' });
  });

  it('removes the gifting when the task fails', async () => {
    const { api, requests } = createApi((r) => {
      const path = new URL(r.url).pathname;
      if (path === '/api/v1/giftings' && r.method === 'POST')
        return Promise.resolve(json({ id: 'g-new' }, 201));
      if (path === '/api/v1/tasks') return Promise.resolve(json({}, 422));
      return Promise.resolve(new Response(null, { status: 500 }));
    });
    const result = await createTaskForGift(api, gift, task);
    expect(result).toMatchObject({ ok: false, status: 422 });
    expect(requests.at(-1)).toMatchObject({
      method: 'DELETE',
      path: '/api/v1/giftings/g-new'
    });
  });

  it('returns the gifting failure without creating a task', async () => {
    const { api, requests } = createApi(() => Promise.resolve(json({}, 404)));
    const result = await createTaskForGift(api, gift, task);
    expect(result.ok).toBe(false);
    expect(requests).toHaveLength(1);
  });
});

describe('parseTaskForm', () => {
  it('defaults status to open and empty due date to null', () => {
    const f = new FormData();
    f.set('title', ' Buy it ');
    expect(parseTaskForm(f)).toEqual({
      values: { title: 'Buy it', status: 'open', due_on: null },
      errors: {}
    });
  });

  it('rejects an unknown status', () => {
    const f = new FormData();
    f.set('title', 'x');
    f.set('status', 'bogus');
    expect(parseTaskForm(f).errors.status).toBe('Bitte wähle einen gültigen Status.');
  });

  it('validates title and due date', () => {
    expect(parseTaskForm(new FormData()).errors.title).toBe('Bitte gib einen Titel an.');
    const f = new FormData();
    f.set('title', 'x'.repeat(201));
    f.set('due_on', '2026-02-31');
    const { errors } = parseTaskForm(f);
    expect(errors.title).toBe('Der Titel darf höchstens 200 Zeichen lang sein.');
    expect(errors.due_on).toBe('Bitte gib ein gültiges Datum an.');
  });
});
