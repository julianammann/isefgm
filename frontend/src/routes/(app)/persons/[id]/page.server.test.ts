import { describe, expect, it, vi } from 'vitest';

import { actions, load } from './+page.server.ts';

type LoadEvent = Parameters<typeof load>[0];
type ActionEvent = Parameters<typeof actions.update>[0];

const ok = (data: unknown) => ({ data, response: new Response(null, { status: 200 }) });
const status = (code: number) => ({ response: new Response(null, { status: code }) });

const person = { id: 'p1', name: 'Lena', birthday: null, relationship: null, notes: null };
const empty = { items: [], total: 0, limit: 200, offset: 0 };
const overview = { given: empty, giftings: empty, ideas: empty, occasions: empty };

/** Load event whose backend answers GET by path. */
function loadEvent(responses: Record<string, unknown>) {
  const GET = vi.fn(async (path: string) => responses[path] ?? status(500));
  return {
    event: {
      locals: { api: { GET } },
      params: { id: 'p1' },
      url: new URL('http://localhost/persons/p1')
    } as unknown as LoadEvent,
    GET
  };
}

describe('load', () => {
  it('returns the person and their view from two parallel requests', async () => {
    const { event, GET } = loadEvent({
      '/api/v1/people/{person_id}': ok(person),
      '/api/v1/people/{person_id}/overview': ok(overview)
    });
    await expect(load(event)).resolves.toEqual({ person, overview, success: null });
    expect(GET).toHaveBeenCalledTimes(2);
  });

  it('answers 404 for an unknown person', async () => {
    const { event } = loadEvent({
      '/api/v1/people/{person_id}': status(404),
      '/api/v1/people/{person_id}/overview': status(404)
    });
    await expect(load(event)).rejects.toMatchObject({ status: 404 });
  });

  it('answers 404 for a malformed id', async () => {
    const { event } = loadEvent({
      '/api/v1/people/{person_id}': status(422),
      '/api/v1/people/{person_id}/overview': status(422)
    });
    await expect(load(event)).rejects.toMatchObject({ status: 404 });
  });
});

/** Update event with the given form fields and a backend that answers PUT with `response`. */
function updateEvent(fields: Record<string, string>, response: unknown) {
  const form = new FormData();
  for (const [key, value] of Object.entries(fields)) form.set(key, value);
  const PUT = vi.fn().mockResolvedValue(response);
  return {
    event: {
      request: new Request('http://localhost/persons/p1', { method: 'POST', body: form }),
      locals: { api: { PUT } },
      params: { id: 'p1' }
    } as unknown as ActionEvent,
    PUT
  };
}

describe('update', () => {
  it('saves the person from the URL and comes back to this page', async () => {
    const { event, PUT } = updateEvent({ name: 'Lena', id: 'other' }, ok(person));
    await expect(actions.update(event)).rejects.toMatchObject({
      status: 303,
      location: '/persons/p1?success=updated'
    });
    expect(PUT.mock.calls[0][1]).toMatchObject({ params: { path: { person_id: 'p1' } } });
  });

  it('keeps the dialog open with field errors and does not call the backend', async () => {
    const { event, PUT } = updateEvent({ name: '  ' }, ok(person));
    await expect(actions.update(event)).resolves.toMatchObject({
      status: 400,
      data: { errors: { name: 'Bitte gib einen Namen an.' } }
    });
    expect(PUT).not.toHaveBeenCalled();
  });

  it('shows the backend error in the dialog', async () => {
    const { event } = updateEvent({ name: 'Lena' }, status(404));
    await expect(actions.update(event)).resolves.toMatchObject({
      status: 404,
      data: { message: 'Person nicht gefunden.', values: { name: 'Lena' } }
    });
  });
});
