import { describe, expect, it } from 'vitest';

import { createApiClient } from '#lib/api/client.js';
import {
  createShareLink,
  deleteShareLink,
  getSharedList,
  isOpen,
  listShareLinks,
  parseShareLinkForm,
  updateShareLink,
  type ShareLink
} from './share-links';

const link: ShareLink = {
  id: '0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a90',
  people: [{ id: 'p1', name: 'Lena' }],
  active: true,
  expires_at: null,
  created_at: '2026-10-04T09:30:00Z'
};

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: { 'Content-Type': 'application/json' }
  });
}

function createApi(handler: (request: Request) => Promise<Response>) {
  const requests: Request[] = [];
  const fetchFn: typeof fetch = (input, init) => {
    const request = input instanceof Request ? input : new Request(input, init);
    requests.push(request);
    return handler(request);
  };
  return { api: createApiClient(fetchFn, 'http://localhost'), requests };
}

/** Form data with repeated `person_ids` and the other fields. */
function formOf(personIds: string[], fields: Record<string, string> = {}): FormData {
  const form = new FormData();
  for (const id of personIds) form.append('person_ids', id);
  for (const [key, value] of Object.entries(fields)) form.set(key, value);
  return form;
}

const now = new Date('2026-11-03T12:00:00Z');

describe('share link requests', () => {
  it('reads every page of the list', async () => {
    const { api, requests } = createApi(async (request) => {
      const offset = Number(new URL(request.url).searchParams.get('offset'));
      return jsonResponse({
        items: offset === 0 ? [link] : [{ ...link, id: 'second' }],
        total: 2,
        limit: 1,
        offset
      });
    });
    const result = await listShareLinks(api);
    expect(result.ok && result.data.map((l) => l.id)).toEqual([link.id, 'second']);
    expect(requests.map((r) => new URL(r.url).searchParams.get('offset'))).toEqual(['0', '1']);
  });

  it('creates a link and returns its token', async () => {
    const { api, requests } = createApi(async () =>
      jsonResponse({ ...link, token: 'secret' }, 201)
    );
    const input = { person_ids: ['p1'], expires_at: null, active: true };
    await expect(createShareLink(api, input)).resolves.toMatchObject({
      ok: true,
      data: { token: 'secret' }
    });
    expect(await requests[0].json()).toEqual(input);
  });

  it('names an expiry in the past', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'past' }, 400));
    await expect(
      updateShareLink(api, link.id, { person_ids: ['p1'], expires_at: null, active: true })
    ).resolves.toMatchObject({
      ok: false,
      status: 400,
      message: 'Das Ablaufdatum darf nicht in der Vergangenheit liegen.'
    });
  });

  it('deletes a link', async () => {
    const { api, requests } = createApi(async () => new Response(null, { status: 204 }));
    await expect(deleteShareLink(api, link.id)).resolves.toEqual({ ok: true, data: null });
    expect(requests[0].method).toBe('DELETE');
  });

  it('says only that an unknown, deactivated or expired token is not valid', async () => {
    const { api, requests } = createApi(async () => jsonResponse({ detail: 'Not found' }, 404));
    await expect(getSharedList(api, 'tok')).resolves.toMatchObject({
      ok: false,
      status: 404,
      message: 'Dieser Link ist nicht gültig oder nicht mehr aktiv.'
    });
    expect(new URL(requests[0].url).pathname).toBe('/api/v1/shared/tok');
  });
});

describe('isOpen', () => {
  it('is open while active and not expired', () => {
    expect(isOpen(link, now)).toBe(true);
    expect(isOpen({ ...link, expires_at: '2026-12-24T22:59:59Z' }, now)).toBe(true);
    expect(isOpen({ ...link, expires_at: '2026-11-01T22:59:59Z' }, now)).toBe(false);
    expect(isOpen({ ...link, active: false }, now)).toBe(false);
  });
});

describe('parseShareLinkForm', () => {
  it('turns the day into the end of that day in German time', () => {
    expect(parseShareLinkForm(formOf(['p1', 'p2'], { expires_on: '2026-12-24' }), now)).toEqual({
      values: { person_ids: ['p1', 'p2'], expires_on: '2026-12-24' },
      expires_at: '2026-12-24T23:59:59+01:00',
      errors: {}
    });
  });

  it('allows no expiry and today', () => {
    expect(parseShareLinkForm(formOf(['p1']), now).expires_at).toBeNull();
    expect(parseShareLinkForm(formOf(['p1'], { expires_on: '2026-11-03' }), now).errors).toEqual(
      {}
    );
  });

  it('needs people, a real date and no day in the past', () => {
    expect(parseShareLinkForm(formOf([]), now).errors.person_ids).toBe(
      'Bitte wähle mindestens eine Person aus.'
    );
    expect(parseShareLinkForm(formOf(['p1'], { expires_on: '2026-02-30' }), now).errors).toEqual({
      expires_on: 'Bitte gib ein gültiges Datum an.'
    });
    expect(parseShareLinkForm(formOf(['p1'], { expires_on: '2026-11-02' }), now).errors).toEqual({
      expires_on: 'Das Datum darf nicht in der Vergangenheit liegen.'
    });
  });

  it('keeps the stored expiry of an edit that does not change the day, even a past one', () => {
    const current = '2026-11-01T22:59:59Z';
    const result = parseShareLinkForm(
      formOf(['p1'], { expires_on: '2026-11-01', current_expires_at: current }),
      now
    );
    expect(result.errors).toEqual({});
    expect(result.expires_at).toBe(current);
  });

  it('counts a person picked twice once', () => {
    expect(parseShareLinkForm(formOf(['p1', 'p1']), now).values.person_ids).toEqual(['p1']);
  });
});
