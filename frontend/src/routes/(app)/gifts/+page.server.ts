import { error, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
  createGift,
  deleteGift,
  giftFromForm,
  listGifts,
  text,
  updateGift,
  type Result
} from '$lib/server/gifts';
import {
  createGifting,
  deleteGifting,
  giftingFromForm,
  groupByGift,
  listGiftings,
  updateGifting,
  type GiftingStatus
} from '$lib/server/giftings';
import { listPersons } from '$lib/server/persons';
import { listOccasions } from '$lib/server/occasions';

const GIVEN_REQUIRED =
  'Für „Verschenkt" werden mindestens eine Empfängerperson, Anlass, Anlasstermin und Verschenkdatum benötigt.';

function isGiftingStatus(status: string | null): status is GiftingStatus {
  return status === 'idea' || status === 'planned' || status === 'acquired' || status === 'given';
}

/** Führt einen API-Aufruf aus und liefert bei einem Fehler ein fail() mit Kontext für die Anzeige. */
async function run(
  action: string,
  id: string | null,
  call: () => Promise<Result<unknown>>,
  on422?: string
) {
  const result = await call();
  if (result.ok) return { action, id, saved: true };
  const message = result.status === 422 && on422 ? on422 : result.message;
  return fail(result.status, { action, id, message });
}

export const load: PageServerLoad = async ({ locals }) => {
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
  return {
    gifts: giftsResult.data,
    giftingsByGift: groupByGift(giftingsResult.data),
    people: peopleResult.data,
    occasions: occasionsResult.data
  };
};

export const actions: Actions = {
  // ── Geschenkideen (F-05) ──────────────────────────────────────

  /** Creates a gift idea with the fields provided in the add-idea dialog. */
  create: async ({ request, locals }) => {
    const body = giftFromForm(await request.formData());
    if (!body.title)
      return fail(400, { action: 'create', id: null, message: 'Bitte einen Titel eingeben.' });
    return run('create', null, () => createGift(locals.api, body));
  },

  update: async ({ request, locals }) => {
    const form = await request.formData();
    const id = text(form, 'id');
    const body = giftFromForm(form);
    if (!id || !body.title)
      return fail(400, { action: 'update', id, message: 'Bitte einen Titel eingeben.' });
    return run('update', id, () => updateGift(locals.api, id, body));
  },

  delete: async ({ request, locals }) => {
    const id = text(await request.formData(), 'id');
    if (!id) return fail(400, { action: 'delete', id, message: 'Keine Idee ausgewählt.' });
    return run('delete', id, () => deleteGift(locals.api, id));
  },

  // ── Beschenkungen (F-06) ──────────────────────────────────────

  /** Creates or updates a gifting with the complete form payload. */
  saveGifting: async ({ request, locals }) => {
    const form = await request.formData();
    const id = text(form, 'gifting_id');
    const giftId = text(form, 'gift_id');
    const status = text(form, 'status');
    if (!giftId) return fail(400, { action: 'saveGifting', id, message: 'Keine Idee ausgewählt.' });
    if (!isGiftingStatus(status))
      return fail(400, {
        action: 'saveGifting',
        id: id ?? giftId,
        message: 'Bitte wähle einen gültigen Status.'
      });
    const body = giftingFromForm(form, giftId);
    return run(
      'saveGifting',
      id ?? giftId,
      () => (id ? updateGifting(locals.api, id, body) : createGifting(locals.api, body)),
      status === 'given' ? GIVEN_REQUIRED : undefined
    );
  },

  deleteGifting: async ({ request, locals }) => {
    const id = text(await request.formData(), 'gifting_id');
    if (!id)
      return fail(400, { action: 'deleteGifting', id, message: 'Keine Beschenkung ausgewählt.' });
    return run('deleteGifting', id, () => deleteGifting(locals.api, id));
  }
};
