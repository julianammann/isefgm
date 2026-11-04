import { hydrate, unmount, type ComponentProps } from 'svelte';
import { afterEach, describe, expect, it } from 'vitest';
import { commands } from 'vitest/browser';

import Page from './+page.svelte';

declare module 'vitest/browser' {
  interface BrowserCommands {
    renderOnServer: (path: string, props: Record<string, unknown>) => Promise<string>;
  }
}

const props = (titles: string[]) =>
  ({
    data: {
      status: { level: 'ok', label: 'Backend und Datenbank erreichbar' },
      user: { id: 'u1', email: 'konto@isefgm.localhost', display_name: 'Konto', created_at: '' },
      page: 2,
      total: 201,
      titles,
      success: null
    },
    form: null,
    params: {}
  }) as unknown as ComponentProps<typeof Page>;

let cleanup = () => {};
afterEach(() => cleanup());

async function hydrated(titles: string[]) {
  const target = document.createElement('div');
  target.innerHTML = await commands.renderOnServer(
    '/src/routes/(app)/ideas/+page.svelte',
    props(titles)
  );
  document.body.append(target);
  const app = hydrate(Page, { target, props: props(titles) });
  cleanup = () => {
    unmount(app);
    target.remove();
  };
  return target;
}

describe('/ideas', () => {
  it('posts each title on its own to adopt it, staying on the page', async () => {
    const target = await hydrated(['Kochbuch', 'Schal']);
    const forms = [...target.querySelectorAll('li form')] as HTMLFormElement[];
    expect(forms.map((f) => new FormData(f).get('title'))).toEqual(['Kochbuch', 'Schal']);
    expect(forms.map((f) => f.getAttribute('action'))).toEqual([
      '?page=2&/adopt',
      '?page=2&/adopt'
    ]);
    expect(forms[0].querySelector('button')?.textContent).toBe('Übernehmen: Kochbuch');
  });

  it('says so when nothing has been given yet', async () => {
    const target = await hydrated([]);
    expect(target.textContent).toContain('Noch keine verschenkten Geschenke.');
  });
});
