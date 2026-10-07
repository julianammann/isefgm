import { beforeEach, describe, expect, it, vi } from 'vitest';

import type * as PersonsModule from './persons';

// TODO(#20): rewrite against a mocked `api` once the real implementation exists

const api = {} as App.Locals['api'];
let persons: typeof PersonsModule;

// Fresh module per test, so the in-memory store starts from the seed data each time.
beforeEach(async () => {
  vi.resetModules();
  persons = await import('./persons');
});

const input = { name: 'Clara Test', birthday: null, notes: null };

describe('listPersons', () => {
  it('returns the seed data', async () => {
    const result = await persons.listPersons(api);
    expect(result.ok && result.data).toHaveLength(2);
  });

  it('returns a copy that does not change the store', async () => {
    const first = await persons.listPersons(api);
    if (first.ok) first.data[0].name = 'geändert';
    const second = await persons.listPersons(api);
    expect(second.ok && second.data[0].name).not.toBe('geändert');
  });
});

describe('createPerson', () => {
  it('adds the person with a new id', async () => {
    const created = await persons.createPerson(api, input);
    expect(created).toMatchObject({ ok: true, data: { ...input, id: expect.any(String) } });
    const list = await persons.listPersons(api);
    expect(list.ok && list.data).toHaveLength(3);
  });
});

describe('updatePerson', () => {
  it('replaces the data of an existing person', async () => {
    const result = await persons.updatePerson(api, '1', input);
    expect(result).toEqual({ ok: true, data: { id: '1', ...input } });
  });

  it('returns 404 for an unknown id', async () => {
    const result = await persons.updatePerson(api, 'unknown', input);
    expect(result).toMatchObject({ ok: false, status: 404 });
  });
});

describe('deletePerson', () => {
  it('removes an existing person', async () => {
    const result = await persons.deletePerson(api, '1');
    expect(result).toEqual({ ok: true, data: null });
    const list = await persons.listPersons(api);
    expect(list.ok && list.data.map((p) => p.id)).toEqual(['2']);
  });

  it('returns 404 for an unknown id', async () => {
    const result = await persons.deletePerson(api, 'unknown');
    expect(result).toMatchObject({ ok: false, status: 404 });
  });
});
