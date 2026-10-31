/**
 * Task data access.
 *
 * Wraps the task endpoints of the backend (`/api/v1/tasks`) and the "task on a bare idea" flow.
 *
 * @module
 */

import type { components } from '$lib/api/schema';
import { text } from './gifts';
import { createGifting, deleteGifting } from './giftings';
import { listAll, send, sendEmpty, type Messages, type Result } from './result';

/** Payload for creating or updating a task. */
export type TaskIn = components['schemas']['TaskIn'];
/** A task as returned by the API. */
export type TaskOut = components['schemas']['TaskOut'];
/** Progress of a task. */
export type TaskStatus = components['schemas']['TaskStatus'];
/** Task data without the gifting it belongs to. */
export type TaskFields = Omit<TaskIn, 'gifting_id'>;
/** Field errors of the task form, keyed by field name. */
export type TaskErrors = Partial<Record<'title' | 'status' | 'due_on', string>>;

type Api = App.Locals['api'];

const messages: Messages = { 404: 'Aufgabe nicht gefunden.' };
const statuses: TaskStatus[] = ['open', 'in_progress', 'done', 'discarded'];

/** Returns all tasks of a gifting; reads every page of the list. */
export function listTasks(api: Api, giftingId: string): Promise<Result<TaskOut[]>> {
  return listAll(
    (offset) =>
      api.GET('/api/v1/tasks', {
        params: { query: { gifting_id: giftingId, limit: 200, offset } }
      }),
    messages
  );
}

/** Creates a task and returns it with its new id. */
export function createTask(api: Api, input: TaskIn): Promise<Result<TaskOut>> {
  return send(api.POST('/api/v1/tasks', { body: input }), messages);
}

/** Replaces a task; 404 if the id is unknown. */
export function updateTask(api: Api, id: string, input: TaskIn): Promise<Result<TaskOut>> {
  return send(
    api.PUT('/api/v1/tasks/{task_id}', { params: { path: { task_id: id } }, body: input }),
    messages
  );
}

/** Deletes a task; 404 if the id is unknown. */
export function deleteTask(api: Api, id: string): Promise<Result<null>> {
  return sendEmpty(
    api.DELETE('/api/v1/tasks/{task_id}', { params: { path: { task_id: id } } }),
    messages
  );
}

function isValidDate(value: string): boolean {
  const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (!match) return false;
  const [year, month, day] = match.slice(1).map(Number);
  const date = new Date(Date.UTC(year, month - 1, day));
  return date.getUTCMonth() === month - 1 && date.getUTCDate() === day;
}

/** Maps the task form to `TaskFields` and validates it; a missing status is `open`. */
export function parseTaskForm(form: FormData): { values: TaskFields; errors: TaskErrors } {
  const title = text(form, 'title') ?? '';
  const status = text(form, 'status') ?? 'open';
  const dueOn = text(form, 'due_on');
  const errors: TaskErrors = {};
  if (title === '') errors.title = 'Bitte gib einen Titel an.';
  else if (title.length > 200) errors.title = 'Der Titel darf höchstens 200 Zeichen lang sein.';
  if (!statuses.includes(status as TaskStatus))
    errors.status = 'Bitte wähle einen gültigen Status.';
  if (dueOn !== null && !isValidDate(dueOn)) errors.due_on = 'Bitte gib ein gültiges Datum an.';
  return { values: { title, status: status as TaskStatus, due_on: dueOn }, errors };
}

/**
 * Creates a task on a bare idea: first an idea-status gifting with the idea's people, then the
 * task on it. If the task fails, the new gifting is removed again and the task's failure returned.
 */
export async function createTaskForGift(
  api: Api,
  gift: { id: string; people: { id: string }[] },
  task: TaskFields
): Promise<Result<TaskOut>> {
  const gifting = await createGifting(api, {
    gift_id: gift.id,
    person_ids: gift.people.map((p) => p.id),
    status: 'idea',
    occasion_id: null,
    occasion_date: null,
    given_on: null
  });
  if (!gifting.ok) return gifting;
  const created = await createTask(api, { ...task, gifting_id: gifting.data.id });
  if (!created.ok) await deleteGifting(api, gifting.data.id);
  return created;
}
