import { describe, expect, it } from 'vitest';
import { page } from 'vitest/browser';
import { render } from 'vitest-browser-svelte';

import { resolve } from '$app/paths';
import { pageQuery } from '$lib/pagination';

import Pagination from './Pagination.svelte';

const href = (p: number) => resolve(`/gifts${pageQuery(p)}`);

describe('Pagination', () => {
  it('renders nothing for a single page', async () => {
    render(Pagination, { page: 1, total: 200, href });
    await expect.element(page.getByRole('navigation', { name: 'Seiten' })).not.toBeInTheDocument();
  });

  it('renders previous, every page and next in the middle', async () => {
    render(Pagination, { page: 2, total: 450, href });
    const nav = page.getByRole('navigation', { name: 'Seiten' });
    await expect.element(nav).toBeInTheDocument();
    const links = nav.getByRole('link').elements();
    expect(links.map((a) => a.textContent?.trim())).toEqual(['Zurück', '1', '2', '3', 'Weiter']);
    await expect
      .element(page.getByRole('link', { name: 'Seite 2' }))
      .toHaveAttribute('aria-current', 'page');
    await expect
      .element(page.getByRole('link', { name: 'Seite 1' }))
      .not.toHaveAttribute('aria-current');
  });

  it('has no previous link on the first page', async () => {
    render(Pagination, { page: 1, total: 450, href });
    await expect.element(page.getByRole('link', { name: 'Zurück' })).not.toBeInTheDocument();
    await expect.element(page.getByRole('link', { name: 'Weiter' })).toBeInTheDocument();
  });

  it('has no next link on the last page', async () => {
    render(Pagination, { page: 3, total: 450, href });
    await expect.element(page.getByRole('link', { name: 'Weiter' })).not.toBeInTheDocument();
    await expect.element(page.getByRole('link', { name: 'Zurück' })).toBeInTheDocument();
  });
});
