import type { ComponentProps } from 'svelte';
import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';

import GiftingsSection from './GiftingsSection.svelte';

const occasion = (id: string, name: string, rule: string | null, date: string | null) => ({
  id,
  name,
  date,
  rule,
  recurrence: 'yearly',
  occasion_type_id: null,
  people: []
});

// Only what the gifting form reads; the full API shapes are not needed here.
const props = {
  gift: { id: 'gift-1', title: 'Kochbuch', people: [] },
  giftings: [],
  tasksByGifting: {},
  people: [],
  occasions: [
    occasion('o-birthday', 'Geburtstag', 'birthday', null),
    occasion('o-christmas', 'Weihnachten', 'christmas', '2026-12-24'),
    occasion('o-easter', 'Ostern', 'easter', '2027-03-28'),
    occasion('o-own', 'Hochzeitstag', null, '2026-06-01')
  ],
  form: null
} as unknown as ComponentProps<typeof GiftingsSection>;

async function openForm() {
  render(GiftingsSection, props);
  await page.getByRole('button', { name: '+ Beschenkung' }).click();
  return {
    occasion: page.getByRole('combobox', { name: 'Anlass (optional)' }),
    date: page.getByLabelText('Anlasstermin (optional)', { exact: true })
  };
}

describe('gifting form', () => {
  it('fills in the next date when Weihnachten or Ostern is picked', async () => {
    const { occasion, date } = await openForm();
    await occasion.selectOptions('Weihnachten');
    await expect.element(date).toHaveValue('2026-12-24');
    await date.fill('2026-12-25');
    await occasion.selectOptions('Ostern');
    await expect.element(date).toHaveValue('2027-03-28');
  });

  it('keeps the entered date for other occasions', async () => {
    const { occasion, date } = await openForm();
    await date.fill('2026-05-01');
    await occasion.selectOptions('Hochzeitstag');
    await expect.element(date).toHaveValue('2026-05-01');
  });
});
