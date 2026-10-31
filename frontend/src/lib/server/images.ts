/**
 * Gift idea images data access.
 *
 * Wraps the image endpoints of the backend (`/api/v1/images`).
 *
 * @module
 */

import type { components } from '$lib/api/schema';
import { imageFileError } from '$lib/images';
import { text } from './gifts';
import { labelError } from './notes';
import { listAll, send, sendEmpty, type Messages, type Result } from './result';

/** An image as returned by the API. */
export type ImageOut = components['schemas']['ImageOut'];
/** Field errors of the image form, keyed by field name. */
export type ImageErrors = Partial<Record<'label' | 'file', string>>;

type Api = App.Locals['api'];

const messages: Messages = {
  404: 'Bild nicht gefunden.',
  409: 'Eine Geschenkidee kann höchstens 5 Bilder haben.',
  413: 'Das Bild ist zu groß. Erlaubt sind höchstens 5 MB und eine begrenzte Auflösung.',
  415: 'Bitte lade ein Bild als JPEG, PNG oder WebP hoch.',
  503: 'Gerade werden zu viele Bilder hochgeladen. Bitte versuche es gleich noch einmal.'
};

/** Returns all images of a gift idea; reads every page of the list. */
export function listImages(api: Api, giftId: string): Promise<Result<ImageOut[]>> {
  return listAll(
    (offset) =>
      api.GET('/api/v1/images', { params: { query: { gift_id: giftId, limit: 200, offset } } }),
    messages
  );
}

/** Uploads an image as multipart form data and returns it with its new id. */
export function createImage(
  api: Api,
  giftId: string,
  label: string,
  file: File
): Promise<Result<ImageOut>> {
  const form = new FormData();
  form.set('gift_id', giftId);
  form.set('label', label);
  form.set('file', file);
  // openapi-fetch passes FormData through unchanged and sets no JSON Content-Type.
  return send(
    api.POST('/api/v1/images', {
      body: form as unknown as components['schemas']['Body_createImage']
    }),
    messages
  );
}

/** Changes the label of an image; 404 if the id is unknown. */
export function updateImageLabel(api: Api, id: string, label: string): Promise<Result<ImageOut>> {
  return send(
    api.PUT('/api/v1/images/{image_id}', {
      params: { path: { image_id: id } },
      body: { label }
    }),
    messages
  );
}

/** Deletes an image; 404 if the id is unknown. */
export function deleteImage(api: Api, id: string): Promise<Result<null>> {
  return sendEmpty(
    api.DELETE('/api/v1/images/{image_id}', { params: { path: { image_id: id } } }),
    messages
  );
}

/** Reads the upload form and validates label and file; the label is trimmed. */
export function parseImageForm(form: FormData): {
  label: string;
  file: File | null;
  errors: ImageErrors;
} {
  const label = text(form, 'label') ?? '';
  const entry = form.get('file');
  const file = entry instanceof File ? entry : null;
  const errors: ImageErrors = {};
  const labelMsg = labelError(label);
  const fileMsg = imageFileError(file);
  if (labelMsg) errors.label = labelMsg;
  if (fileMsg) errors.file = fileMsg;
  return { label, file, errors };
}
