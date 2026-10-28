import { describe, it, expect } from 'vitest';

describe('Phase 1 Frontend stubs', () => {
  it('utils - severityClass maps correctly', () => {
    const { severityClass } = await import('@/lib/utils');
    expect(severityClass('critical')).toContain('severity-critical');
    expect(severityClass('healthy')).toContain('severity-healthy');
  });

  it('utils - formatNumber handles numbers', () => {
    const { formatNumber } = await import('@/lib/utils');
    expect(formatNumber(1234.5678, 2)).toEqual('1,234.57');
  });
});
