/**
 * Gift idea notes data access.
 *
 * Wraps the note endpoints of the backend (`/api/v1/notes`).
 *
 * @module
 */

import type { components } from '$lib/api/schema';
import { text } from './gifts';
import { listAll, send, sendEmpty, type Messages, type Result } from './result';

/** Payload for creating or updating a note. */
export type NoteIn = components['schemas']['NoteIn'];
/** A note as returned by the API. */
export type NoteOut = components['schemas']['NoteOut'];
/** Field errors of the note form, keyed by field name. */
export type NoteErrors = Partial<Record<'label' | 'text', string>>;

type Api = App.Locals['api'];

const messages: Messages = { 404: 'Notiz nicht gefunden.' };

/** Returns all notes of a gift idea; reads every page of the list. */
export function listNotes(api: Api, giftId: string): Promise<Result<NoteOut[]>> {
  return listAll(
    (offset) =>
      api.GET('/api/v1/notes', { params: { query: { gift_id: giftId, limit: 200, offset } } }),
    messages
  );
}

/** Creates a note and returns it with its new id. */
export function createNote(api: Api, input: NoteIn): Promise<Result<NoteOut>> {
  return send(api.POST('/api/v1/notes', { body: input }), messages);
}

/** Replaces a note; 404 if the id is unknown. */
export function updateNote(api: Api, id: string, input: NoteIn): Promise<Result<NoteOut>> {
  return send(
    api.PUT('/api/v1/notes/{note_id}', { params: { path: { note_id: id } }, body: input }),
    messages
  );
}

/** Deletes a note; 404 if the id is unknown. */
export function deleteNote(api: Api, id: string): Promise<Result<null>> {
  return sendEmpty(
    api.DELETE('/api/v1/notes/{note_id}', { params: { path: { note_id: id } } }),
    messages
  );
}

/** Validates a label (shared by notes and links); returns a message or undefined if it is fine. */
export function labelError(label: string): string | undefined {
  if (label === '') return 'Bitte gib eine Bezeichnung an.';
  if (label.length > 100) return 'Die Bezeichnung darf höchstens 100 Zeichen lang sein.';
  return undefined;
}

function textError(value: string): string | undefined {
  if (value === '') return 'Bitte gib einen Text an.';
  if (value.length > 2000) return 'Der Text darf höchstens 2000 Zeichen lang sein.';
  return undefined;
}

/** Maps the note form to `NoteIn` and validates it; `values` are trimmed, empty ones become ''. */
export function parseNoteForm(
  form: FormData,
  giftId: string
): { values: NoteIn; errors: NoteErrors } {
  const values: NoteIn = {
    gift_id: giftId,
    label: text(form, 'label') ?? '',
    text: text(form, 'text') ?? ''
  };
  const errors: NoteErrors = {};
  const label = labelError(values.label);
  const body = textError(values.text);
  if (label) errors.label = label;
  if (body) errors.text = body;
  return { values, errors };
}
