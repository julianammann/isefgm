import { describe, expect, it } from 'vitest';
import { occasionDateLabel } from './occasion-date';

describe('occasionDateLabel', () => {
  it('says the birthday date comes from each person', () => {
    expect(occasionDateLabel({ rule: 'birthday', date: null })).toBe('Datum je Person');
  });
  it('shows Christmas without a year', () => {
    expect(occasionDateLabel({ rule: 'christmas', date: '2026-12-24' })).toBe('24.12.');
  });
  it('shows Easter with its year', () => {
    expect(occasionDateLabel({ rule: 'easter', date: '2027-03-28' })).toBe('28.03.2027');
  });
  it('shows an own occasion with its stored date', () => {
    expect(occasionDateLabel({ rule: null, date: '2021-01-07' })).toBe('07.01.2021');
  });
});
