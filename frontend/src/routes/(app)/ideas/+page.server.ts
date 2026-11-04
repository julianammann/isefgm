/**
 * Ideas page (`/ideas`): titles of gifts given in any account, to adopt as an own gift idea
 * with one click (F-16).
 *
 * @module
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { createGift, listGivenTitlesPage } from '#lib/server/gifts.js';
import { pageCount, pageQuery, parsePage } from '#lib/pagination.js';

/** Loads one page of titles (`?page=N`; beyond the last page redirects to it). */
export const load: PageServerLoad = async ({ locals, url }) => {
  const page = parsePage(url);
  const result = await listGivenTitlesPage(locals.api, page);
  if (!result.ok) error(result.status, result.message);

  const { items, total } = result.data;
  if (total > 0 && page > pageCount(total)) redirect(303, '/ideas' + pageQuery(pageCount(total)));

  return {
    page,
    total,
    titles: items,
    success: url.searchParams.get('success') === 'adopted' ? 'Als Geschenkidee übernommen!' : null
  };
};

/** `adopt`: creates an own gift idea with only the posted title and stays on the page. */
export const actions: Actions = {
  adopt: async ({ request, locals, url }) => {
    const title = String((await request.formData()).get('title') ?? '');
    const result = await createGift(locals.api, { title, category: 'other' });
    if (!result.ok) return fail(result.status, { message: result.message });
    throw redirect(303, '/ideas' + pageQuery(parsePage(url), { success: 'adopted' }));
  }
};
