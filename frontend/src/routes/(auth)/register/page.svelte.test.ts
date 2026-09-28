import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';

import Page from './+page.svelte';

const data = (registrationEnabled: boolean) => ({
  status: { level: 'ok' as const, label: 'Backend und Datenbank erreichbar' },
  registrationEnabled
});

describe('/register', () => {
  it('shows the form while registration is open', async () => {
    render(Page, { data: data(true), form: null, params: {} });
    await expect.element(page.getByRole('button', { name: 'Konto anlegen' })).toBeInTheDocument();
  });

  it('says it is closed instead of showing the form', async () => {
    render(Page, { data: data(false), form: null, params: {} });
    await expect
      .element(page.getByText('Die Registrierung ist derzeit geschlossen.'))
      .toBeInTheDocument();
    await expect
      .element(page.getByRole('button', { name: 'Konto anlegen' }))
      .not.toBeInTheDocument();
    await expect.element(page.getByRole('link', { name: 'Anmelden' })).toBeInTheDocument();
  });
});
