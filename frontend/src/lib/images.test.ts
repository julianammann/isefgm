import { describe, expect, it } from 'vitest';

import { imageFileError, MAX_IMAGE_BYTES } from './images';

const file = (size: number, type: string) => new File([new Uint8Array(size)], 'a.jpg', { type });

describe('imageFileError', () => {
  it('accepts 5 MB exactly', () => {
    expect(imageFileError(file(MAX_IMAGE_BYTES, 'image/jpeg'))).toBeUndefined();
  });

  it('rejects one byte more', () => {
    expect(imageFileError(file(MAX_IMAGE_BYTES + 1, 'image/jpeg'))).toBe(
      'Das Bild ist zu groß. Erlaubt sind höchstens 5 MB.'
    );
  });

  it('rejects HEIC', () => {
    expect(imageFileError(file(10, 'image/heic'))).toBe(
      'Bitte wähle ein Bild als JPEG, PNG oder WebP.'
    );
  });

  it('rejects no file', () => {
    expect(imageFileError(null)).toBe('Bitte wähle ein Bild aus.');
    expect(imageFileError(file(0, 'image/png'))).toBe('Bitte wähle ein Bild aus.');
  });

  it('lets an empty type pass', () => {
    expect(imageFileError(file(10, ''))).toBeUndefined();
  });
});
