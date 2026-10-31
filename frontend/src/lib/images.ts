/**
 * Image upload limits and the browser-side file check.
 *
 * Free of server imports, so it can run in the browser as well.
 *
 * @module
 */

/** Maximum number of images per gift idea. */
export const MAX_IMAGES = 5;
/** Maximum upload size in bytes. */
export const MAX_IMAGE_BYTES = 5 * 1024 * 1024;
/** Accepted MIME types. */
export const IMAGE_TYPES = ['image/jpeg', 'image/png', 'image/webp'];

/** Returns a German message if the file cannot be uploaded; an empty type passes, the backend checks the content. */
export function imageFileError(file: File | null): string | undefined {
  if (!file || file.size === 0) return 'Bitte wähle ein Bild aus.';
  if (file.size > MAX_IMAGE_BYTES) return 'Das Bild ist zu groß. Erlaubt sind höchstens 5 MB.';
  if (file.type !== '' && !IMAGE_TYPES.includes(file.type)) {
    return 'Bitte wähle ein Bild als JPEG, PNG oder WebP.';
  }
  return undefined;
}
