/**
 * Gift ideas page (`/gifts`): list, create, edit and delete gift ideas (F-04, F-05)
 * and their giftings (F-06).
 *
 * @module
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import {
  createGift,
  deleteGift,
  giftFromForm,
  listGifts,
  updateGift,
  type GiftIn
} from '$lib/server/gifts';
import {
  createGifting,
  deleteGifting,
  giftingFromForm,
  groupByGift,
  listGiftings,
  updateGifting,
  type GiftingIn
} from '$lib/server/giftings';
import { listPersons } from '$lib/server/persons';
import { listOccasions } from '$lib/server/occasions';

type FieldErrors = Partial<Record<keyof GiftIn, string>>;
type GiftingFieldErrors = Partial<Record<keyof GiftingIn, string>>;

/**
 * Display messages for `?success=<key>` after a redirect. Only the key travels in the URL,
 * so the page cannot be made to show arbitrary text and the `Location` header stays ASCII.
 */
const successMessages = {
  created: 'Geschenkidee angelegt!',
  updated: 'Änderungen gespeichert!',
  deleted: 'Geschenkidee gelöscht!',
  giftingCreated: 'Beschenkung angelegt!',
  giftingUpdated: 'Änderungen an der Beschenkung gespeichert!',
  giftingDeleted: 'Beschenkung gelöscht!'
} as const;

type SuccessKey = keyof typeof successMessages;

function isSuccessKey(key: string | null): key is SuccessKey {
  return key !== null && Object.prototype.hasOwnProperty.call(successMessages, key);
}

/** Reads and validates the gift idea form. The backend remains the authority on validation. */
function parseForm(form: FormData): { values: GiftIn; errors: FieldErrors } {
  const values = giftFromForm(form);
  const priceFrom = values.price_from === null ? null : Number(values.price_from);
  const priceTo = values.price_to === null ? null : Number(values.price_to);
  const errors: FieldErrors = {};

  if (!values.title) errors.title = 'Bitte gib einen Titel an.';
  else if (values.title.length > 200) {
    errors.title = 'Der Titel darf höchstens 200 Zeichen lang sein.';
  }
  if (values.description && values.description.length > 2000) {
    errors.description = 'Die Beschreibung darf höchstens 2000 Zeichen lang sein.';
  }
  if (priceFrom !== null && !(priceFrom >= 0)) {
    errors.price_from = 'Bitte gib einen gültigen Preis an.';
  }
  if (priceTo !== null && !(priceTo >= 0)) errors.price_to = 'Bitte gib einen gültigen Preis an.';
  else if (priceFrom !== null && priceTo !== null && priceFrom > priceTo) {
    errors.price_to = '„Preis bis“ darf nicht kleiner als „Preis von“ sein.';
  }
  if (values.currency && !/^[A-Z]{3}$/.test(values.currency)) {
    errors.currency = 'Bitte gib einen Währungscode aus drei Buchstaben an, z. B. EUR.';
  }
  return { values, errors };
}

const GIFTING_STATUSES = ['idea', 'planned', 'acquired', 'given'] as const;

/**
 * Reads and validates the gifting form. A given gifting needs recipients, an occasion, its
 * date and the day it was given, like the backend checks. The backend remains the authority.
 */
function parseGiftingForm(form: FormData): { values: GiftingIn; errors: GiftingFieldErrors } {
  const status = String(form.get('status') ?? '');
  const values = giftingFromForm(form, String(form.get('gift_id') ?? ''));
  const errors: GiftingFieldErrors = {};

  if (!values.gift_id) errors.gift_id = 'Keine Geschenkidee ausgewählt.';
  if (!(GIFTING_STATUSES as readonly string[]).includes(status)) {
    errors.status = 'Bitte wähle einen gültigen Status.';
  }
  if (values.occasion_date && Number.isNaN(Date.parse(values.occasion_date))) {
    errors.occasion_date = 'Bitte gib ein gültiges Datum an.';
  }
  if (values.given_on && Number.isNaN(Date.parse(values.given_on))) {
    errors.given_on = 'Bitte gib ein gültiges Datum an.';
  }
  if (values.status === 'given') {
    if (!values.person_ids?.length) {
      errors.person_ids = 'Für „Verschenkt“ bitte mindestens eine Person auswählen.';
    }
    if (!values.occasion_id) errors.occasion_id = 'Für „Verschenkt“ bitte einen Anlass wählen.';
    if (!values.occasion_date) {
      errors.occasion_date ??= 'Für „Verschenkt“ bitte den Anlasstermin angeben.';
    }
    if (!values.given_on) errors.given_on ??= 'Für „Verschenkt“ bitte das Verschenkdatum angeben.';
  }
  return { values, errors };
}

/**
 * Loads gift ideas, giftings, people and occasions. `?edit=<id>` returns one idea and
 * `?edit_gifting=<id>` one gifting for the edit form.
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
  const editGiftingId = url.searchParams.get('edit_gifting');
  const gifting = giftingsResult.data.find((g) => g.id === editGiftingId);
  const editingGifting: (GiftingIn & { id: string }) | null = gifting
    ? {
        id: gifting.id,
        gift_id: gifting.gift.id,
        status: gifting.status,
        person_ids: gifting.people.map((person) => person.id),
        occasion_id: gifting.occasion?.id ?? null,
        occasion_date: gifting.occasion_date,
        given_on: gifting.given_on
      }
    : null;
  const success = url.searchParams.get('success');

  return {
    editing,
    editingGifting,
    success: isSuccessKey(success) ? successMessages[success] : null,
    gifts: giftsResult.data,
    giftingsByGift: groupByGift(giftingsResult.data),
    people: peopleResult.data,
    occasions: occasionsResult.data
  };
};

export const actions: Actions = {
  // ── Geschenkideen (F-05) ──────────────────────────────────────
  // `create` / `update`: validate the form and save the idea; field errors return with 400.
  // `delete`: removes the idea; confirmation happens in the page dialog.

  create: async ({ request, locals }) => {
    const { values, errors } = parseForm(await request.formData());
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await createGift(locals.api, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    throw redirect(303, '/gifts?success=created');
  },

  update: async ({ request, locals }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const { values, errors } = parseForm(form);
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
  },

  // ── Beschenkungen (F-06) ──────────────────────────────────────
  // Same flow as the gift ideas; the form keys are prefixed so both dialogs keep their state.

  createGifting: async ({ request, locals }) => {
    const { values, errors } = parseGiftingForm(await request.formData());
    if (Object.keys(errors).length) {
      return fail(400, { giftingValues: values, giftingErrors: errors });
    }
    const result = await createGifting(locals.api, values);
    if (!result.ok) {
      return fail(result.status, { giftingValues: values, giftingMessage: result.message });
    }
    throw redirect(303, '/gifts?success=giftingCreated');
  },

  updateGifting: async ({ request, locals }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const { values, errors } = parseGiftingForm(form);
    if (Object.keys(errors).length) {
      return fail(400, { giftingValues: values, giftingErrors: errors });
    }
    const result = await updateGifting(locals.api, id, values);
    if (!result.ok) {
      return fail(result.status, { giftingValues: values, giftingMessage: result.message });
    }
    throw redirect(303, '/gifts?success=giftingUpdated');
  },

  deleteGifting: async ({ request, locals }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteGifting(locals.api, id);
    if (!result.ok) return fail(result.status, { deleteMessage: result.message });
    throw redirect(303, '/gifts?success=giftingDeleted');
  }
};
