/**
 * Gift idea detail page (`/gifts/<id>`): the idea itself and its giftings (F-05, F-06), notes,
 * links and images (F-07) and the tasks of its giftings (F-08).
 *
 * @module
 */
import { error, fail, redirect } from '@sveltejs/kit';
import type { Actions, PageServerLoad } from './$types';
import { deleteGift, getGift, parseGiftForm, updateGift } from '$lib/server/gifts';
import {
  createGifting,
  deleteGifting,
  listGiftings,
  parseGiftingForm,
  updateGifting
} from '$lib/server/giftings';
import { listPersons } from '$lib/server/persons';
import { listOccasions } from '$lib/server/occasions';
import {
  createNote,
  deleteNote,
  labelError,
  listNotes,
  parseNoteForm,
  updateNote
} from '$lib/server/notes';
import { createLink, deleteLink, listLinks, parseLinkForm, updateLink } from '$lib/server/links';
import {
  createImage,
  deleteImage,
  listImages,
  parseImageForm,
  updateImageLabel
} from '$lib/server/images';
import {
  createTask,
  createTaskForGift,
  deleteTask,
  listTasks,
  parseTaskForm,
  updateTask
} from '$lib/server/tasks';
import type { Result } from '$lib/server/result';

/**
 * Display messages for `?success=<key>` after a redirect. Only the key travels in the URL,
 * so the page cannot be made to show arbitrary text and the `Location` header stays ASCII.
 */
const successMessages = {
  updated: 'Änderungen gespeichert!',
  giftingCreated: 'Beschenkung angelegt!',
  giftingUpdated: 'Änderungen an der Beschenkung gespeichert!',
  giftingDeleted: 'Beschenkung gelöscht!',
  noteCreated: 'Notiz angelegt!',
  noteUpdated: 'Notiz gespeichert!',
  noteDeleted: 'Notiz gelöscht!',
  linkCreated: 'Link angelegt!',
  linkUpdated: 'Link gespeichert!',
  linkDeleted: 'Link gelöscht!',
  imageCreated: 'Bild hochgeladen!',
  imageUpdated: 'Bild gespeichert!',
  imageDeleted: 'Bild gelöscht!',
  taskCreated: 'Aufgabe angelegt!',
  taskUpdated: 'Aufgabe gespeichert!',
  taskDeleted: 'Aufgabe gelöscht!'
} as const;

type SuccessKey = keyof typeof successMessages;

function isSuccessKey(key: string | null): key is SuccessKey {
  return key !== null && Object.prototype.hasOwnProperty.call(successMessages, key);
}

/** The dialog a failed action belongs to; `delete` covers every delete confirmation. */
type Scope = 'gift' | 'gifting' | 'note' | 'link' | 'image' | 'task' | 'delete';

// Not exported: SvelteKit rejects other exports from +page.server.ts; all actions live here.

/** Fails an action; the page shows `values`, `errors` and `message` only in the dialog of `scope`. */
function detailFail<
  S extends Scope,
  D extends { values?: object; errors?: object; message?: string }
>(status: number, scope: S, data: D) {
  return fail(status, { scope, ...data });
}

/** Redirects back to the detail page of idea `id`, which then shows the message for `key`. */
function detailRedirect(id: string, key: SuccessKey): never {
  redirect(303, `/gifts/${encodeURIComponent(id)}?success=${key}`);
}

/** Returns the data of a successful result; a failure becomes SvelteKit's error page. */
function unwrap<T>(result: Result<T>): T {
  if (!result.ok) error(result.status, result.message);
  return result.data;
}

/**
 * Loads the idea with its giftings, notes, links and images, the tasks of each gifting, and the
 * people and occasions for the forms. An unknown idea gives a 404 page.
 */
export const load: PageServerLoad = async ({ locals, params, url }) => {
  const [giftResult, giftingsResult, peopleResult, occasionsResult, notes, links, images] =
    await Promise.all([
      getGift(locals.api, params.id),
      listGiftings(locals.api),
      listPersons(locals.api),
      listOccasions(locals.api),
      listNotes(locals.api, params.id),
      listLinks(locals.api, params.id),
      listImages(locals.api, params.id)
    ]);
  // A malformed id (not a UUID) gets 422 from the backend; for the user it is just unknown.
  if (!giftResult.ok && giftResult.status === 422) error(404, 'Geschenkidee nicht gefunden.');
  const gift = unwrap(giftResult);
  // The backend cannot filter giftings by idea, so the full list is filtered here.
  const giftings = unwrap(giftingsResult).filter((g) => g.gift.id === params.id);
  const tasks = await Promise.all(giftings.map((g) => listTasks(locals.api, g.id)));
  const success = url.searchParams.get('success');

  return {
    gift,
    giftings,
    tasksByGifting: Object.fromEntries(giftings.map((g, i) => [g.id, unwrap(tasks[i])])),
    notes: unwrap(notes),
    links: unwrap(links),
    images: unwrap(images),
    people: unwrap(peopleResult),
    occasions: unwrap(occasionsResult),
    success: isSuccessKey(success) ? successMessages[success] : null
  };
};

/**
 * Every action takes the idea from the URL and the id of the edited item from the form field
 * `id`. A success redirects back to this page with a `?success=` key (only `delete` leaves for
 * the list); a failure returns its `scope`, so the page shows the error in the right dialog.
 *
 * `update`: validates and saves the idea. `delete`: removes the idea and returns to the list;
 * 409 while a gifting still uses it.
 *
 * `createNote` / `updateNote` / `deleteNote` and the `*Link` actions: notes and links of this
 * idea.
 *
 * `createImage`: uploads an image (multipart, file checked here as well). `updateImage`
 * changes only its label, the backend allows nothing else. `deleteImage` removes it.
 *
 * `createGifting` / `updateGifting` / `deleteGifting`: the giftings of this idea.
 *
 * `createTask` / `updateTask` / `deleteTask`: the tasks of a gifting, named by the form field
 * `gifting_id`. `createTaskForGift`: on an idea without giftings, creates a gifting with status
 * `idea` and the task on it; if the task fails, the new gifting is deleted again.
 */
export const actions: Actions = {
  createImage: async ({ request, locals, params }) => {
    const { label, file, errors } = parseImageForm(await request.formData());
    // A file input cannot be refilled, so only the label is returned.
    const values = { label };
    if (Object.keys(errors).length || !file) return detailFail(400, 'image', { values, errors });
    const result = await createImage(locals.api, params.id, label, file);
    if (!result.ok) return detailFail(result.status, 'image', { values, message: result.message });
    detailRedirect(params.id, 'imageCreated');
  },

  updateImage: async ({ request, locals, params }) => {
    const form = await request.formData();
    const label = String(form.get('label') ?? '').trim();
    const labelMsg = labelError(label);
    const values = { label };
    if (labelMsg) return detailFail(400, 'image', { values, errors: { label: labelMsg } });
    const result = await updateImageLabel(locals.api, String(form.get('id') ?? ''), label);
    if (!result.ok) return detailFail(result.status, 'image', { values, message: result.message });
    detailRedirect(params.id, 'imageUpdated');
  },

  deleteImage: async ({ request, locals, params }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteImage(locals.api, id);
    if (!result.ok) return detailFail(result.status, 'delete', { message: result.message });
    detailRedirect(params.id, 'imageDeleted');
  },

  update: async ({ request, locals, params }) => {
    const { values, errors } = parseGiftForm(await request.formData());
    if (Object.keys(errors).length) return detailFail(400, 'gift', { values, errors });
    const result = await updateGift(locals.api, params.id, values);
    if (!result.ok) return detailFail(result.status, 'gift', { values, message: result.message });
    detailRedirect(params.id, 'updated');
  },

  delete: async ({ locals, params }) => {
    const result = await deleteGift(locals.api, params.id);
    if (!result.ok) return detailFail(result.status, 'delete', { message: result.message });
    redirect(303, '/gifts?success=deleted');
  },

  createNote: async ({ request, locals, params }) => {
    const { values, errors } = parseNoteForm(await request.formData(), params.id);
    if (Object.keys(errors).length) return detailFail(400, 'note', { values, errors });
    const result = await createNote(locals.api, values);
    if (!result.ok) return detailFail(result.status, 'note', { values, message: result.message });
    detailRedirect(params.id, 'noteCreated');
  },

  updateNote: async ({ request, locals, params }) => {
    const form = await request.formData();
    const { values, errors } = parseNoteForm(form, params.id);
    if (Object.keys(errors).length) return detailFail(400, 'note', { values, errors });
    const result = await updateNote(locals.api, String(form.get('id') ?? ''), values);
    if (!result.ok) return detailFail(result.status, 'note', { values, message: result.message });
    detailRedirect(params.id, 'noteUpdated');
  },

  deleteNote: async ({ request, locals, params }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteNote(locals.api, id);
    if (!result.ok) return detailFail(result.status, 'delete', { message: result.message });
    detailRedirect(params.id, 'noteDeleted');
  },

  createLink: async ({ request, locals, params }) => {
    const { values, errors } = parseLinkForm(await request.formData(), params.id);
    if (Object.keys(errors).length) return detailFail(400, 'link', { values, errors });
    const result = await createLink(locals.api, values);
    if (!result.ok) return detailFail(result.status, 'link', { values, message: result.message });
    detailRedirect(params.id, 'linkCreated');
  },

  updateLink: async ({ request, locals, params }) => {
    const form = await request.formData();
    const { values, errors } = parseLinkForm(form, params.id);
    if (Object.keys(errors).length) return detailFail(400, 'link', { values, errors });
    const result = await updateLink(locals.api, String(form.get('id') ?? ''), values);
    if (!result.ok) return detailFail(result.status, 'link', { values, message: result.message });
    detailRedirect(params.id, 'linkUpdated');
  },

  deleteLink: async ({ request, locals, params }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteLink(locals.api, id);
    if (!result.ok) return detailFail(result.status, 'delete', { message: result.message });
    detailRedirect(params.id, 'linkDeleted');
  },

  createGifting: async ({ request, locals, params }) => {
    const form = await request.formData();
    form.set('gift_id', params.id);
    const { values, errors } = parseGiftingForm(form);
    if (Object.keys(errors).length) return detailFail(400, 'gifting', { values, errors });
    const result = await createGifting(locals.api, values);
    if (!result.ok) {
      return detailFail(result.status, 'gifting', { values, message: result.message });
    }
    detailRedirect(params.id, 'giftingCreated');
  },

  updateGifting: async ({ request, locals, params }) => {
    const form = await request.formData();
    form.set('gift_id', params.id);
    const { values, errors } = parseGiftingForm(form);
    if (Object.keys(errors).length) return detailFail(400, 'gifting', { values, errors });
    const result = await updateGifting(locals.api, String(form.get('id') ?? ''), values);
    if (!result.ok) {
      return detailFail(result.status, 'gifting', { values, message: result.message });
    }
    detailRedirect(params.id, 'giftingUpdated');
  },

  deleteGifting: async ({ request, locals, params }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteGifting(locals.api, id);
    if (!result.ok) return detailFail(result.status, 'delete', { message: result.message });
    detailRedirect(params.id, 'giftingDeleted');
  },

  createTask: async ({ request, locals, params }) => {
    const form = await request.formData();
    const { values, errors } = parseTaskForm(form);
    if (Object.keys(errors).length) return detailFail(400, 'task', { values, errors });
    const gifting_id = String(form.get('gifting_id') ?? '');
    const result = await createTask(locals.api, { ...values, gifting_id });
    if (!result.ok) return detailFail(result.status, 'task', { values, message: result.message });
    detailRedirect(params.id, 'taskCreated');
  },

  updateTask: async ({ request, locals, params }) => {
    const form = await request.formData();
    const { values, errors } = parseTaskForm(form);
    if (Object.keys(errors).length) return detailFail(400, 'task', { values, errors });
    const gifting_id = String(form.get('gifting_id') ?? '');
    const result = await updateTask(locals.api, String(form.get('id') ?? ''), {
      ...values,
      gifting_id
    });
    if (!result.ok) return detailFail(result.status, 'task', { values, message: result.message });
    detailRedirect(params.id, 'taskUpdated');
  },

  deleteTask: async ({ request, locals, params }) => {
    const id = String((await request.formData()).get('id') ?? '');
    const result = await deleteTask(locals.api, id);
    if (!result.ok) return detailFail(result.status, 'delete', { message: result.message });
    detailRedirect(params.id, 'taskDeleted');
  },

  createTaskForGift: async ({ request, locals, params }) => {
    const { values, errors } = parseTaskForm(await request.formData());
    if (Object.keys(errors).length) return detailFail(400, 'task', { values, errors });
    const gift = unwrap(await getGift(locals.api, params.id));
    const result = await createTaskForGift(locals.api, gift, values);
    if (!result.ok) return detailFail(result.status, 'task', { values, message: result.message });
    detailRedirect(params.id, 'taskCreated');
  }
};
