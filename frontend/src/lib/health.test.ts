import { describe, expect, it } from 'vitest';

import { systemStatus } from './health.ts';

describe('systemStatus', () => {
  it('is ok when backend and database answer', () => {
    expect(systemStatus({ status: 'ok', database: true })).toEqual({
      level: 'ok',
      label: 'Backend und Datenbank erreichbar'
    });
  });

  it('is degraded when the database does not answer', () => {
    expect(systemStatus({ status: 'degraded', database: false }).level).toBe('degraded');
  });

  it('is down when the backend does not answer', () => {
    expect(systemStatus(null)).toEqual({ level: 'down', label: 'Backend nicht erreichbar' });
  });
});
