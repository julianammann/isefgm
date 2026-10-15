/**
 * Occasions page: list, create, update, delete (F-03).
 *
 * @module
 */

import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

import { listPersons } from '$lib/server/persons';
import {
  createOccasion,
  deleteOccasion,
  getOccasion,
  listOccasions,
  listOccasionTypes,
  updateOccasion,
  type OccasionInput
} from '$lib/server/occasions';

type FieldErrors = Partial<Record<keyof OccasionInput | 'general', string>>;

/**
 * Display messages for `?success=<key>` after a redirect. Only the key travels in the URL,
 * so the page cannot be made to show arbitrary text and the `Location` header stays ASCII.
 */
const successMessages = {
  created: 'Anlass angelegt!',
  updated: 'Änderungen gespeichert!',
  deleted: 'Anlass gelöscht!'
} as const;

type SuccessKey = keyof typeof successMessages;

function isSuccessKey(key: string | null): key is SuccessKey {
  return key !== null && Object.prototype.hasOwnProperty.call(successMessages, key);
}

/** Reads and validates the occasion form. The backend remains the authority on validation. */
function parseForm(form: FormData): { values: OccasionInput; errors: FieldErrors } {
  const name = String(form.get('name') ?? '').trim();
  const date = String(form.get('date') ?? '').trim();
  const occasionTypeId = String(form.get('occasion_type_id') ?? '').trim() || null;
  const recurrence = String(form.get('recurrence') ?? '');
  const personIds = form.getAll('person_ids').map(String).filter(Boolean);
  const errors: FieldErrors = {};

  if (!name) errors.name = 'Bitte gib einen Namen an.';
  else if (name.length > 100) errors.name = 'Der Name darf höchstens 100 Zeichen lang sein.';
  if (!date) errors.date = 'Bitte gib ein Datum an.';
  else if (Number.isNaN(Date.parse(date))) {
    errors.date = 'Bitte gib ein gültiges Datum an.';
  }
  if (recurrence !== 'none' && recurrence !== 'yearly') {
    errors.recurrence = 'Bitte wähle eine gültige Wiederholung.';
  }
  return {
    values: {
      name,
      date,
      occasion_type_id: occasionTypeId,
      person_ids: personIds,
      recurrence: recurrence === 'yearly' ? 'yearly' : 'none'
    },
    errors
  };
}

/** Loads all occasions; `?edit=<id>` returns one for the edit form. */
export const load: PageServerLoad = async ({ locals, url }) => {
  const result = await listOccasions(locals.api);
  if (!result.ok) error(result.status, result.message);
  const occasions = result.data;

  const typesResult = await listOccasionTypes(locals.api);
  if (!typesResult.ok) error(typesResult.status, typesResult.message);
  const occasionTypes = typesResult.data;

  const peopleResult = await listPersons(locals.api);
  if (!peopleResult.ok) error(peopleResult.status, peopleResult.message);
  const people = peopleResult.data;

  const editId = url.searchParams.get('edit');
  let editOccasion: (OccasionInput & { id: string }) | null = null;
  if (editId) {
    const occasionResult = await getOccasion(locals.api, editId);
    if (!occasionResult.ok) error(occasionResult.status, occasionResult.message);
    editOccasion = {
      id: occasionResult.data.id,
      name: occasionResult.data.name,
      date: occasionResult.data.date,
      occasion_type_id: occasionResult.data.occasion_type_id,
      person_ids: occasionResult.data.people.map((person) => person.id),
      recurrence: occasionResult.data.recurrence
    };
  }

  const successKey = url.searchParams.get('success');
  const successMessage = isSuccessKey(successKey) ? successMessages[successKey] : null;

  return { occasions, occasionTypes, people, editOccasion, successMessage };
};

/** Handles form submissions for creating, updating, and deleting occasions. */
export const actions: Actions = {
  create: async ({ request, locals }) => {
    const form = await request.formData();
    const { values, errors } = parseForm(form);

    if (Object.keys(errors).length > 0) {
      return fail(400, { values, errors });
    }

    const result = await createOccasion(locals.api, values);
    if (!result.ok) {
      const actionErrors: FieldErrors = { general: result.message };
      return fail(result.status, { values, errors: actionErrors });
    }

    throw redirect(303, `?success=created`);
  },

  update: async ({ request, locals }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '').trim();
    const { values, errors } = parseForm(form);

    if (!id) {
      const actionErrors: FieldErrors = { general: 'Ungültige Anfrage.' };
      return fail(400, { values, errors: actionErrors });
    }

    if (Object.keys(errors).length > 0) {
      return fail(400, { values, errors });
    }

    const result = await updateOccasion(locals.api, id, values);
    if (!result.ok) {
      const actionErrors: FieldErrors = { general: result.message };
      return fail(result.status, { values, errors: actionErrors });
    }

    throw redirect(303, `?success=updated`);
  },

  delete: async ({ request, locals }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '').trim();

    if (!id) {
      const errors: FieldErrors = { general: 'Ungültige Anfrage.' };
      return fail(400, { errors });
    }

    const result = await deleteOccasion(locals.api, id);
    if (!result.ok) {
      const errors: FieldErrors = { general: result.message };
      return fail(result.status, { errors });
    }

    throw redirect(303, `?success=deleted`);
  }
};
