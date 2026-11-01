import { describe, expect, it } from 'vitest';

import { createApiClient } from '$lib/api/client';
import type { Person, PersonInput } from './persons';
import {
  createPerson,
  deletePerson,
  getPerson,
  getPersonOverview,
  listPersons,
  listPersonsPage,
  parsePersonForm,
  updatePerson
} from './persons';

const firstPerson: Person = {
  id: '0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70',
  name: 'Clara Test',
  birthday: null,
  relationship: 'Freundin',
  notes: null,
  created_at: '2026-10-04T09:30:00Z'
};

const secondPerson: Person = {
  ...firstPerson,
  id: '0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a71',
  name: 'Lena Test'
};

const input: PersonInput = {
  name: 'Clara Test',
  birthday: null,
  relationship: 'Freundin',
  notes: null
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

  return { api: createApiClient(fetchFn, 'http://api.test'), requests };
}

describe('listPersons', () => {
  it('loads every page using the number of collected persons as the next offset', async () => {
    const { api, requests } = createApi(async (request) => {
      const offset = new URL(request.url).searchParams.get('offset');
      if (offset === '0') {
        return jsonResponse({ items: [firstPerson], offset: 0, limit: 1, total: 2 });
      }
      return jsonResponse({ items: [secondPerson], offset: 1, limit: 1, total: 2 });
    });

    const result = await listPersons(api);

    expect(result).toEqual({ ok: true, data: [firstPerson, secondPerson] });
    expect(requests).toHaveLength(2);
    expect(requests.map((request) => new URL(request.url).searchParams.get('offset'))).toEqual([
      '0',
      '1'
    ]);
  });

  it('returns the backend error for a failed page request', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'Unauthorized' }, 401));

    await expect(listPersons(api)).resolves.toEqual({
      ok: false,
      status: 401,
      message: 'Sitzung abgelaufen. Bitte erneut anmelden.'
    });
  });
});

describe('getPerson', () => {
  it('returns a person by id', async () => {
    const { api, requests } = createApi(async () => jsonResponse(firstPerson));

    await expect(getPerson(api, firstPerson.id)).resolves.toEqual({
      ok: true,
      data: firstPerson
    });
    expect(new URL(requests[0].url).pathname).toBe(`/api/v1/people/${firstPerson.id}`);
  });

  it('maps a network failure to 502', async () => {
    const { api } = createApi(async () => {
      throw new TypeError('Failed to fetch');
    });

    await expect(getPerson(api, firstPerson.id)).resolves.toMatchObject({
      ok: false,
      status: 502
    });
  });

  it('rejects a successful response without the expected body', async () => {
    const { api } = createApi(async () => new Response(null, { status: 204 }));

    await expect(getPerson(api, firstPerson.id)).resolves.toMatchObject({
      ok: false,
      status: 502
    });
  });
});

describe('getPersonOverview', () => {
  it('asks for one page of up to 200 entries per list', async () => {
    const empty = { items: [], total: 0, limit: 200, offset: 0 };
    const overview = { given: empty, giftings: empty, ideas: empty, occasions: empty };
    const { api, requests } = createApi(async () => jsonResponse(overview));

    await expect(getPersonOverview(api, firstPerson.id)).resolves.toEqual({
      ok: true,
      data: overview
    });
    const url = new URL(requests[0].url);
    expect(url.pathname).toBe(`/api/v1/people/${firstPerson.id}/overview`);
    expect(url.searchParams.get('limit')).toBe('200');
  });

  it('returns 404 for an unknown person', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'Not found' }, 404));

    await expect(getPersonOverview(api, firstPerson.id)).resolves.toMatchObject({
      ok: false,
      status: 404,
      message: 'Person nicht gefunden.'
    });
  });
});

describe('createPerson', () => {
  it('sends the person fields and returns the created person', async () => {
    const { api, requests } = createApi(async () => jsonResponse(firstPerson, 201));

    await expect(createPerson(api, input)).resolves.toEqual({
      ok: true,
      data: firstPerson
    });
    expect(requests[0].method).toBe('POST');
    await expect(requests[0].clone().json()).resolves.toEqual(input);
  });
});

describe('updatePerson', () => {
  it('replaces the person fields', async () => {
    const { api, requests } = createApi(async () => jsonResponse(firstPerson));

    await expect(updatePerson(api, firstPerson.id, input)).resolves.toEqual({
      ok: true,
      data: firstPerson
    });
    expect(requests[0].method).toBe('PUT');
    await expect(requests[0].clone().json()).resolves.toEqual(input);
  });

  it('returns 404 for an unknown person', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'Not found' }, 404));

    await expect(updatePerson(api, firstPerson.id, input)).resolves.toMatchObject({
      ok: false,
      status: 404
    });
  });
});

describe('deletePerson', () => {
  it('deletes a person with an empty success response', async () => {
    const { api, requests } = createApi(async () => new Response(null, { status: 204 }));

    await expect(deletePerson(api, firstPerson.id)).resolves.toEqual({
      ok: true,
      data: null
    });
    expect(requests[0].method).toBe('DELETE');
    expect(new URL(requests[0].url).pathname).toBe(`/api/v1/people/${firstPerson.id}`);
  });

  it('returns 404 for an unknown person', async () => {
    const { api } = createApi(async () => jsonResponse({ detail: 'Not found' }, 404));

    await expect(deletePerson(api, firstPerson.id)).resolves.toMatchObject({
      ok: false,
      status: 404
    });
  });
});

describe('listPersonsPage', () => {
  it('requests one page of 200 and returns items with the total', async () => {
    const { api, requests } = createApi(async () =>
      jsonResponse({ items: [firstPerson], offset: 200, limit: 200, total: 450 })
    );

    await expect(listPersonsPage(api, 2)).resolves.toEqual({
      ok: true,
      data: { items: [firstPerson], total: 450 }
    });
    const query = new URL(requests[0].url).searchParams;
    expect(requests).toHaveLength(1);
    expect([query.get('limit'), query.get('offset')]).toEqual(['200', '200']);
  });

  it('sends limit=200 when loading every page', async () => {
    const { api, requests } = createApi(async () =>
      jsonResponse({ items: [firstPerson], offset: 0, limit: 200, total: 1 })
    );

    await listPersons(api);
    expect(new URL(requests[0].url).searchParams.get('limit')).toBe('200');
  });
});

describe('parsePersonForm', () => {
  it('trims the fields and turns empty optional ones into null', () => {
    const form = new FormData();
    form.set('name', '  Lena ');
    form.set('relationship', ' ');
    expect(parsePersonForm(form)).toEqual({
      values: { name: 'Lena', birthday: null, relationship: null, notes: null },
      errors: {}
    });
  });

  it('requires a name of at most 100 characters', () => {
    const form = new FormData();
    expect(parsePersonForm(form).errors.name).toBe('Bitte gib einen Namen an.');
    form.set('name', 'x'.repeat(101));
    expect(parsePersonForm(form).errors.name).toBe(
      'Der Name darf höchstens 100 Zeichen lang sein.'
    );
  });
});
