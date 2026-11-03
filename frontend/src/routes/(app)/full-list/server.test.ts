import { spawnSync } from 'node:child_process';
import { createRequire } from 'node:module';
import { describe, expect, it, vi } from 'vitest';

import type { components } from '#lib/api/schema.js';
import { GET } from './+server.ts';

type Event = Parameters<typeof GET>[0];
type FullList = components['schemas']['FullListOut'];

const vnuJar = createRequire(import.meta.url).resolve('vnu-jar/build/dist/vnu.jar');

const person = { id: 'p1', name: 'Testperson' };
const birthday = { id: 'o1', name: 'Geburtstag' };

const filled: FullList = {
  people: [
    {
      ...person,
      birthday: '2000-11-10',
      relationship: 'Schwester',
      notes: 'Trinkt gern Tee',
      created_at: '2026-10-01T08:00:00Z'
    }
  ],
  gifts: [
    {
      id: 'g1',
      title: 'Kriminalroman',
      description: 'Taschenbuch',
      price_from: '10.00',
      price_to: '20.00',
      currency: 'EUR',
      category: 'books',
      people: [person],
      occasions: [birthday],
      links: [{ id: 'l1', gift_id: 'g1', label: 'Shop', url: 'https://example.org/buch' }],
      notes: [{ id: 'n1', gift_id: 'g1', label: 'Format', text: 'A5' }],
      created_at: '2026-10-01T08:00:00Z'
    }
  ],
  given: [
    {
      id: 'x1',
      gift: { id: 'g1', title: 'Kriminalroman' },
      status: 'given',
      people: [person],
      occasion: birthday,
      occasion_date: '2025-11-10',
      given_on: '2025-11-09',
      created_at: '2025-10-01T08:00:00Z'
    }
  ]
};

const empty: FullList = { people: [], gifts: [], given: [] };

/** Request event whose backend answers the full list with `status` and `data`. */
function fakeEvent(status: number, data?: FullList) {
  const api = {
    GET: vi.fn().mockResolvedValue({ data, response: new Response(null, { status }) })
  };
  return { event: { locals: { api } } as unknown as Event, api };
}

async function documentFor(list: FullList) {
  const response = await GET(fakeEvent(200, list).event);
  return { response, html: await response.text() };
}

/** Messages of the Nu Html Checker, the engine behind validator.w3.org. */
function w3cMessages(html: string): unknown[] {
  const result = spawnSync('java', ['-jar', vnuJar, '--stdout', '--format', 'json', '-'], {
    input: html,
    encoding: 'utf8'
  });
  return JSON.parse(result.stdout).messages;
}

describe('GET /full-list', () => {
  it('loads the full list from the backend', async () => {
    const { event, api } = fakeEvent(200, empty);
    await GET(event);
    expect(api.GET).toHaveBeenCalledWith('/api/v1/full-list');
  });

  it('answers with one self-contained German HTML document', async () => {
    const { response, html } = await documentFor(empty);
    expect(response.headers.get('content-type')).toBe('text/html; charset=utf-8');
    expect(html).toMatch(/^<!doctype html>\s*<html lang="de">/);
    expect(html).toContain('<title>Vollständige Liste – Geschenke-Manager</title>');
    expect(html).toMatch(/<style[^>]*>/);
  });

  it('shows people, gift ideas and past gifts', async () => {
    const { html } = await documentFor(filled);
    for (const text of [
      'Personen',
      'Testperson',
      '10.11.2000',
      'Schwester',
      'Trinkt gern Tee',
      'Geschenkideen',
      'Kriminalroman',
      'Taschenbuch',
      'Bücher',
      '10,00 – 20,00 EUR',
      'Geburtstag',
      'href="https://example.org/buch"',
      'Format',
      'A5',
      'Vergangene Geschenke',
      '10.11.2025',
      '09.11.2025'
    ]) {
      expect(html).toContain(text);
    }
  });

  it('says so when a section is empty', async () => {
    const { html } = await documentFor(empty);
    expect(html).toContain('Keine Personen.');
    expect(html).toContain('Keine Geschenkideen.');
    expect(html).toContain('Keine vergangenen Geschenke.');
  });

  it('escapes text entered by the account', async () => {
    const list = { ...empty, people: [{ ...filled.people[0], name: '<script>alert(1)</script>' }] };
    const { html } = await documentFor(list);
    expect(html).not.toContain('<script>alert(1)');
    expect(html).toContain('&lt;script>alert(1)');
  });

  it('turns a backend failure into an error page', async () => {
    await expect(GET(fakeEvent(503).event)).rejects.toMatchObject({ status: 503 });
  });

  it.each([
    ['filled', filled],
    ['empty', empty]
  ])('passes the W3C validator with a %s list (QZ-03)', { timeout: 30_000 }, async (_, list) => {
    const { html } = await documentFor(list);
    expect(w3cMessages(html)).toEqual([]);
  });
});
