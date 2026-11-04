/**
 * Persons page (`/persons`): list, create, edit and delete persons (F-02), and share the ideas of
 * a person through a read-only link (F-14).
 *
 * @module
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';

import {
  createPerson,
  deletePerson,
  listPersons,
  listPersonsPage,
  parsePersonForm,
  updatePerson
} from '#lib/server/persons.js';
import { pageCount, pageQuery, parsePage } from '#lib/pagination.js';
import { unwrap } from '#lib/server/result.js';
import { shareAction } from '#lib/server/share-links.js';

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

/**
 * Loads one page of persons; `?edit=<id>` returns one of them for the edit form. All persons are
 * loaded as well, so the share dialog can add people from other pages.
 */
export const load: PageServerLoad = async ({ locals, url }) => {
  const page = parsePage(url);
  const [result, everyone] = await Promise.all([
    listPersonsPage(locals.api, page),
    listPersons(locals.api)
  ]);
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
    people: unwrap(everyone).map(({ id, name }) => ({ id, name })),
    success: isSuccessKey(success) ? successMessages[success] : null,
    // The toast turns red after a delete, so removing a person does not look like saving one.
    deleted: success === 'deleted'
  };
};

/**
 * `create` / `update`: validate the form and save the person; field errors return with 400.
 *
 * `delete`: removes the person; confirmation happens in the page dialog.
 *
 * `share`: creates a share link and returns its URL (see `shareAction`).
 */
export const actions: Actions = {
  create: async ({ request, locals }) => {
    const { values, errors } = parsePersonForm(await request.formData());
    if (Object.keys(errors).length) return fail(400, { values, errors });
    const result = await createPerson(locals.api, values);
    if (!result.ok) return fail(result.status, { values, message: result.message });
    throw redirect(303, '/persons?success=created');
  },
  update: async ({ request, locals, url }) => {
    const form = await request.formData();
    const id = String(form.get('id') ?? '');
    const { values, errors } = parsePersonForm(form);
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
  },
  share: async ({ request, locals, url }) =>
    shareAction(locals.api, await request.formData(), url.origin)
};
