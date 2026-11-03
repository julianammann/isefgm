import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';

import Page from './+page.svelte';

const data = {
  status: { level: 'ok' as const, label: 'Backend und Datenbank erreichbar' },
  user: {
    id: 'u1',
    email: 'konto@isefgm.localhost',
    display_name: 'Konto',
    created_at: '2026-01-01T00:00:00Z'
  },
  persons: [],
  page: 1,
  total: 0,
  editing: null,
  success: null,
  deleted: false
};

/** What a create rejected for its birthday leaves in `form`. */
const failedCreate = {
  values: { name: 'Lena', birthday: '2026-02-30', relationship: null, notes: null },
  errors: { birthday: 'Bitte gib ein gültiges Datum an.' }
};

describe('/persons', () => {
  it('opens an empty form again after a failed create', async () => {
    render(Page, { data, form: failedCreate, params: {} });
    await page.getByRole('button', { name: 'Person hinzufügen' }).click();
    await expect.element(page.getByRole('dialog')).toBeVisible();
    await expect.element(page.getByLabelText('Name')).toHaveValue('');
    await expect
      .element(page.getByText('Bitte gib ein gültiges Datum an.'))
      .not.toBeInTheDocument();
  });

  it('keeps the open dialog with its errors after a failed submit', async () => {
    const screen = render(Page, { data, form: null, params: {} });
    await page.getByRole('button', { name: 'Person hinzufügen' }).click();
    await screen.rerender({ data, form: failedCreate, params: {} });
    await expect.element(page.getByRole('dialog')).toBeVisible();
    await expect.element(page.getByLabelText('Name')).toHaveValue('Lena');
    await expect.element(page.getByText('Bitte gib ein gültiges Datum an.')).toBeInTheDocument();
  });
});
