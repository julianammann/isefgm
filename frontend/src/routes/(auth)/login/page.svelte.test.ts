import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';

import Page from './+page.svelte';

const data = (registrationEnabled: boolean) => ({
  status: { level: 'ok' as const, label: 'Backend und Datenbank erreichbar' },
  registrationEnabled
});

describe('/login', () => {
  it('links to the registration while it is open', async () => {
    render(Page, { data: data(true), form: null, params: {} });
    await expect.element(page.getByRole('link', { name: 'Registrieren' })).toBeInTheDocument();
  });

  it('hides the link while registration is closed', async () => {
    render(Page, { data: data(false), form: null, params: {} });
    await expect.element(page.getByRole('button', { name: 'Anmelden' })).toBeInTheDocument();
    await expect.element(page.getByRole('link', { name: 'Registrieren' })).not.toBeInTheDocument();
  });
});
