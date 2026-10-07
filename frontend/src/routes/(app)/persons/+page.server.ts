/**
 * Persons page (`/persons`): list, create, edit and delete persons (F-02).
 *
 * @module
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

import {
  createPerson,
  deletePerson,
  listPersons,
  updatePerson,
  type PersonInput
} from '$lib/server/persons';

type FieldErrors = Partial<Record<keyof PersonInput, string>>;

/** Reads and validates the person form. The backend remains the authority on validation. */
function parseForm(form: FormData): { values: PersonInput; errors: FieldErrors } {
  const name = String(form.get('name') ?? '').trim();
  const birthday = String(form.get('birthday') ?? '').trim() || null;
  const notes = String(form.get('notes') ?? '').trim() || null;
  const errors: FieldErrors = {};

  if (!name) errors.name = 'Bitte gib einen Namen an.';
  else if (name.length > 100) errors.name = 'Der Name darf höchstens 100 Zeichen lang sein.';
  if (birthday && Number.isNaN(Date.parse(birthday))) {
    errors.birthday = 'Bitte gib ein gültiges Datum an.';
  }
  return { values: { name, birthday, notes }, errors };
}

/** Loads all persons; `?edit=<id>` preselects one for the edit form. */
export const load: PageServerLoad = async ({ locals, url }) => {
  const result = await listPersons(locals.api);
  if (!result.ok) error(result.status, result.message);
  const editId = url.searchParams.get('edit');
  const success = url.searchParams.get('success');
  return {
    persons: result.data,
    editing: result.data.find((p) => p.id === editId) ?? null,
    success
  };
};

/**
 * `create` / `update`: validate the form and save the person; field errors return with 400.
 *
 * `delete`: removes the person; confirmation happens in the page dialog.
 */
export const actions: Actions = {
  create: async ({ request, locals }) => {
    const { values, errors } = parseForm(await request.formData());
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await createPerson(locals.api, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    throw redirect(303, '/persons?success=Person+angelegt!');
  },
  update: async ({ request, locals }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const { values, errors } = parseForm(form);
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await updatePerson(locals.api, id, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    throw redirect(303, '/persons?success=Änderungen+gespeichert!');
  },
  delete: async ({ request, locals }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deletePerson(locals.api, id);
    if (!result.ok) return fail(result.status, { deleteMessage: result.message });
    throw redirect(303, '/persons?success=Person+gelöscht!');
  }
};
