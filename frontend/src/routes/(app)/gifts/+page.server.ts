import { error, fail } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
  ApiError,
  createGift,
  deleteGift,
  giftFromForm,
  listAllGifts,
  text,
  updateGift
} from '$lib/server/gifts';
import {
  createGifting,
  deleteGifting,
  giftingFromForm,
  groupByGift,
  listAllGiftings,
  updateGifting,
  type GiftingStatus
} from '$lib/server/giftings';
import { listPersons } from '$lib/server/persons';
import { listOccasions } from '$lib/server/occasions';

const MESSAGES: Record<number, string> = {
  404: 'Eintrag nicht gefunden.',
  409: 'Die Idee wird von mindestens einer Beschenkung verwendet und kann nicht gelöscht werden.',
  422: 'Angaben unvollständig oder ungültig.'
};
const GIVEN_REQUIRED =
  'Für „Verschenkt" werden mindestens eine Empfängerperson, Anlass, Anlasstermin und Verschenkdatum benötigt.';

function isGiftingStatus(status: string | null): status is GiftingStatus {
  return status === 'idea' || status === 'planned' || status === 'acquired' || status === 'given';
}

/** Führt einen API-Aufruf aus und liefert bei ApiError ein fail() mit Kontext für die Anzeige. */
async function run(
  action: string,
  id: string | null,
  call: () => Promise<unknown>,
  on422 = MESSAGES[422]
) {
  try {
    await call();
    return { action, id, saved: true };
  } catch (e) {
    if (!(e instanceof ApiError)) throw e;
    const message = e.status === 422 ? on422 : (MESSAGES[e.status] ?? 'Speichern fehlgeschlagen.');
    return fail(e.status, { action, id, message });
  }
}

export const load: PageServerLoad = async ({ fetch, locals }) => {
  try {
    const [gifts, giftings, peopleResult, occasionsResult] = await Promise.all([
      listAllGifts(fetch),
      listAllGiftings(fetch),
      listPersons(locals.api),
      listOccasions(locals.api)
    ]);
    if (!peopleResult.ok) error(peopleResult.status, peopleResult.message);
    if (!occasionsResult.ok) error(occasionsResult.status, occasionsResult.message);
    return {
      gifts,
      giftingsByGift: groupByGift(giftings),
      people: peopleResult.data,
      occasions: occasionsResult.data
    };
  } catch (e) {
    if (e instanceof ApiError) error(502, 'Geschenkideen konnten nicht geladen werden.');
    throw e;
  }
};

export const actions: Actions = {
  // ── Geschenkideen (F-05) ──────────────────────────────────────

  /** Creates a gift idea with the fields provided in the add-idea dialog. */
  create: async ({ request, fetch }) => {
    const body = giftFromForm(await request.formData());
    if (!body.title)
      return fail(400, { action: 'create', id: null, message: 'Bitte einen Titel eingeben.' });
    return run('create', null, () => createGift(fetch, body));
  },

  update: async ({ request, fetch }) => {
    const form = await request.formData();
    const id = text(form, 'id');
    const body = giftFromForm(form);
    if (!id || !body.title)
      return fail(400, { action: 'update', id, message: 'Bitte einen Titel eingeben.' });
    return run('update', id, () => updateGift(fetch, id, body));
  },

  delete: async ({ request, fetch }) => {
    const id = text(await request.formData(), 'id');
    if (!id) return fail(400, { action: 'delete', id, message: 'Keine Idee ausgewählt.' });
    return run('delete', id, () => deleteGift(fetch, id));
  },

  // ── Beschenkungen (F-06) ──────────────────────────────────────

  /** Creates or updates a gifting with the complete form payload. */
  saveGifting: async ({ request, fetch }) => {
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
      () => (id ? updateGifting(fetch, id, body) : createGifting(fetch, body)),
      status === 'given' ? GIVEN_REQUIRED : MESSAGES[422]
    );
  },

  deleteGifting: async ({ request, fetch }) => {
    const id = text(await request.formData(), 'gifting_id');
    if (!id)
      return fail(400, { action: 'deleteGifting', id, message: 'Keine Beschenkung ausgewählt.' });
    return run('deleteGifting', id, () => deleteGifting(fetch, id));
  }
};
