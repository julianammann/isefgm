import { describe, expect, it } from 'vitest';

import { MAX_PAGE, PAGE_SIZE, actionUrl, pageCount, pageQuery, parsePage } from './pagination';

const url = (search: string) => new URL(`http://x.test/gifts${search}`);

describe('parsePage', () => {
  it('reads a positive integer', () => expect(parsePage(url('?page=2'))).toBe(2));
  it('defaults to 1 when missing', () => expect(parsePage(url(''))).toBe(1));
  it('caps a huge page so the offset stays a safe integer', () => {
    const page = parsePage(url('?page=5000000000000000000'));
    expect(page).toBe(MAX_PAGE);
    expect((page - 1) * PAGE_SIZE).toBeLessThanOrEqual(Number.MAX_SAFE_INTEGER);
  });
  it.each(['0', '-1', 'abc', '2.5', ''])('treats %j as page 1', (value) => {
    expect(parsePage(url(`?page=${value}`))).toBe(1);
  });
});

describe('pageCount', () => {
  it.each([
    [0, 1],
    [200, 1],
    [201, 2],
    [450, 3]
  ])('%i entries -> %i pages', (total, pages) => expect(pageCount(total)).toBe(pages));
});

describe('pageQuery', () => {
  it('omits page 1', () => expect(pageQuery(1)).toBe(''));
  it('adds the page', () => expect(pageQuery(2)).toBe('?page=2'));
  it('appends extra params after the page', () => {
    expect(pageQuery(2, { edit: 'x' })).toBe('?page=2&edit=x');
  });
  it('keeps extras on page 1', () => {
    expect(pageQuery(1, { success: 'deleted' })).toBe('?success=deleted');
  });
});

describe('actionUrl', () => {
  it('has no page param on page 1', () => expect(actionUrl('update', 1)).toBe('?/update'));
  it('carries the page', () => expect(actionUrl('update', 3)).toBe('?page=3&/update'));
});
