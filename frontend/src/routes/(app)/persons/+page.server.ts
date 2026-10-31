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
  listPersonsPage,
  updatePerson,
  type PersonInput
} from '$lib/server/persons';
import { pageCount, pageQuery, parsePage } from '$lib/pagination';

type FieldErrors = Partial<Record<keyof PersonInput, string>>;

/**
 * Display messages for `?success=<key>` after a redirect. Only the key travels in the URL,
 * so the page cannot be made to show arbitrary text and the `Location` header stays ASCII.
 */
const successMessages = {
  created: 'Person angelegt!',
  updated: 'Änderungen gespeichert!',
  deleted: 'Person gelöscht!'
} as const;

type SuccessKey = keyof typeof successMessages;

function isSuccessKey(key: string | null): key is SuccessKey {
  return key !== null && Object.prototype.hasOwnProperty.call(successMessages, key);
}

/** Reads and validates the person form. The backend remains the authority on validation. */
function parseForm(form: FormData): { values: PersonInput; errors: FieldErrors } {
  const name = String(form.get('name') ?? '').trim();
  const birthday = String(form.get('birthday') ?? '').trim() || null;
  const relationship = String(form.get('relationship') ?? '').trim() || null;
  const notes = String(form.get('notes') ?? '').trim() || null;
  const errors: FieldErrors = {};

  if (!name) errors.name = 'Bitte gib einen Namen an.';
  else if (name.length > 100) errors.name = 'Der Name darf höchstens 100 Zeichen lang sein.';
  if (birthday && Number.isNaN(Date.parse(birthday))) {
    errors.birthday = 'Bitte gib ein gültiges Datum an.';
  }
  if (relationship && relationship.length > 100) {
    errors.relationship = 'Die Beziehung darf höchstens 100 Zeichen lang sein.';
  }
  if (notes && notes.length > 2000) {
    errors.notes = 'Notizen dürfen höchstens 2000 Zeichen lang sein.';
  }
  return { values: { name, birthday, relationship, notes }, errors };
}

/** Loads one page of persons; `?edit=<id>` returns one of them for the edit form. */
export const load: PageServerLoad = async ({ locals, url }) => {
  const page = parsePage(url);
  const result = await listPersonsPage(locals.api, page);
  if (!result.ok) error(result.status, result.message);
  const { items, total } = result.data;
  const last = pageCount(total);
  if (total > 0 && page > last) {
    const rest = Object.fromEntries([...url.searchParams].filter(([key]) => key !== 'page'));
    redirect(303, '/persons' + pageQuery(last, rest));
  }
  const editId = url.searchParams.get('edit');
  const success = url.searchParams.get('success');
  return {
    persons: items,
    page,
    total,
    editing: items.find((p) => p.id === editId) ?? null,
    success: isSuccessKey(success) ? successMessages[success] : null
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
    throw redirect(303, '/persons?success=created');
  },
  update: async ({ request, locals, url }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const { values, errors } = parseForm(form);
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await updatePerson(locals.api, id, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    throw redirect(303, '/persons' + pageQuery(parsePage(url), { success: 'updated' }));
  },
  delete: async ({ request, locals, url }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deletePerson(locals.api, id);
    if (!result.ok) return fail(result.status, { deleteMessage: result.message });
    throw redirect(303, '/persons' + pageQuery(parsePage(url), { success: 'deleted' }));
  }
};
