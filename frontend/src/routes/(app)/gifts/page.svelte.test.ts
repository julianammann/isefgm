import { hydrate, unmount, type ComponentProps } from 'svelte';
import { afterEach, describe, expect, it, vi } from 'vitest';
import { commands } from 'vitest/browser';

import Page from './+page.svelte';

declare module 'vitest/browser' {
  interface BrowserCommands {
    renderOnServer: (path: string, props: Record<string, unknown>) => Promise<string>;
  }
}

const gift = (id: string, title: string) => ({
  id,
  title,
  category: 'books',
  people: [],
  occasions: []
});

/** Both lines start with a status that has no count („○ Idee“); the second has a separator. */
const props = {
  data: {
    status: { level: 'ok', label: 'Backend und Datenbank erreichbar' },
    user: { id: 'u1', email: 'konto@isefgm.localhost', display_name: 'Konto', created_at: '' },
    editing: null,
    success: null,
    page: 1,
    total: 2,
    gifts: [gift('g1', 'Buch'), gift('g2', 'Schal')],
    giftingsByGift: {
      g1: [{ status: 'idea' }],
      g2: [{ status: 'idea' }, { status: 'planned' }, { status: 'planned' }]
    },
    people: [],
    occasions: []
  },
  form: null,
  params: {}
  // Only the fields the list renders; the full API types add nothing to this test.
} as unknown as ComponentProps<typeof Page>;

let cleanup = () => {};
afterEach(() => cleanup());

/** Hydrates the server HTML of the page, like the browser does after SvelteKit's SSR. */
async function hydrated() {
  const target = document.createElement('div');
  target.innerHTML = await commands.renderOnServer('/src/routes/(app)/gifts/+page.svelte', props);
  document.body.append(target);
  const warn = vi.spyOn(console, 'warn');
  const app = hydrate(Page, { target, props });
  cleanup = () => {
    unmount(app);
    target.remove();
    warn.mockRestore();
  };
  return { target, warnings: warn.mock.calls.flat().map(String).join('\n') };
}

describe('/gifts', () => {
  it('hydrates the server HTML of ideas whose first status has no count', async () => {
    const { warnings } = await hydrated();
    expect(warnings).not.toContain('Failed to hydrate');
  });

  it('keeps counts and separators in the gifting line', async () => {
    const { target } = await hydrated();
    const lines = [...target.querySelectorAll('p')].map((p) =>
      p.textContent.replace(/\s+/g, ' ').trim()
    );
    expect(lines).toContain('1 Beschenkung: ○ Idee');
    expect(lines).toContain('3 Beschenkungen: ○ Idee · 2× ◔ Geplant');
  });
});
