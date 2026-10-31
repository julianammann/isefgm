/**
 * Gift ideas page (`/gifts`): overview, create, edit and delete gift ideas (F-04, F-05).
 * Giftings are managed on the detail page.
 *
 * @module
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
  createGift,
  deleteGift,
  listGifts,
  parseGiftForm,
  updateGift,
  type GiftIn
} from '$lib/server/gifts';
import { groupByGift, listGiftings } from '$lib/server/giftings';
import { listPersons } from '$lib/server/persons';
import { listOccasions } from '$lib/server/occasions';

/**
 * Display messages for `?success=<key>` after a redirect. Only the key travels in the URL,
 * so the page cannot be made to show arbitrary text and the `Location` header stays ASCII.
 */
const successMessages = {
  created: 'Geschenkidee angelegt!',
  updated: 'Änderungen gespeichert!',
  deleted: 'Geschenkidee gelöscht!'
} as const;

type SuccessKey = keyof typeof successMessages;

function isSuccessKey(key: string | null): key is SuccessKey {
  return key !== null && Object.prototype.hasOwnProperty.call(successMessages, key);
}

/**
 * Loads gift ideas, giftings, people and occasions. `?edit=<id>` returns one idea for the
 * edit form.
 */
export const load: PageServerLoad = async ({ locals, url }) => {
  const [giftsResult, giftingsResult, peopleResult, occasionsResult] = await Promise.all([
    listGifts(locals.api),
    listGiftings(locals.api),
    listPersons(locals.api),
    listOccasions(locals.api)
  ]);
  if (!giftsResult.ok) error(giftsResult.status, giftsResult.message);
  if (!giftingsResult.ok) error(giftingsResult.status, giftingsResult.message);
  if (!peopleResult.ok) error(peopleResult.status, peopleResult.message);
  if (!occasionsResult.ok) error(occasionsResult.status, occasionsResult.message);

  const editId = url.searchParams.get('edit');
  const gift = giftsResult.data.find((g) => g.id === editId);
  const editing: (GiftIn & { id: string }) | null = gift
    ? {
        id: gift.id,
        title: gift.title,
        description: gift.description,
        category: gift.category,
        price_from: gift.price_from,
        price_to: gift.price_to,
        currency: gift.currency,
        person_ids: gift.people.map((person) => person.id),
        occasion_ids: gift.occasions.map((occasion) => occasion.id)
      }
    : null;
  const success = url.searchParams.get('success');

  return {
    editing,
    success: isSuccessKey(success) ? successMessages[success] : null,
    gifts: giftsResult.data,
    giftingsByGift: groupByGift(giftingsResult.data),
    people: peopleResult.data,
    occasions: occasionsResult.data
  };
};

/**
 * `create` / `update`: validate the form and save the gift idea; field errors return with 400.
 *
 * `delete`: removes the gift idea; confirmation happens in the page dialog. 409 while a
 * gifting still uses it.

 */
export const actions: Actions = {
  // ── Gift ideas (F-05) ─────────────────────────────────────────

  create: async ({ request, locals }) => {
    const { values, errors } = parseGiftForm(await request.formData());
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await createGift(locals.api, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    throw redirect(303, '/gifts?success=created');
  },

  update: async ({ request, locals }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const { values, errors } = parseGiftForm(form);
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await updateGift(locals.api, id, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    throw redirect(303, '/gifts?success=updated');
  },

  delete: async ({ request, locals }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteGift(locals.api, id);
    if (!result.ok) return fail(result.status, { deleteMessage: result.message });
    throw redirect(303, '/gifts?success=deleted');
  }
};
