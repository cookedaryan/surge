import { describe, it, expect } from 'vitest';
import { formatMoney, isNotCosted, NOT_COSTED } from './money';

/**
 * Costs used to be printed as `$${value ?? 0}`, which was wrong twice over: the fallback turned an
 * unpriced network into a confident $0.00, and the symbol was dollars while the catalogue prices in
 * rupees.
 */
describe('formatMoney', () => {
  it('reads as not costed when there is no figure', () => {
    // The whole point. A zero here says the network is free; null says nobody priced it, and only
    // one of those is a thing that can be true.
    expect(formatMoney(null, 'INR')).toBe(NOT_COSTED);
    expect(formatMoney(undefined, 'INR')).toBe(NOT_COSTED);
    expect(formatMoney(Number.NaN, 'INR')).toBe(NOT_COSTED);
  });

  it('distinguishes a real zero from an absent figure', () => {
    // A costed run genuinely reporting 0 is a different statement from an uncosted one.
    expect(formatMoney(0, 'INR')).not.toBe(NOT_COSTED);
    expect(formatMoney(0, 'INR')).toContain('0');
  });

  it('labels the figure with the currency it is actually in', () => {
    const rendered = formatMoney(396393.79, 'INR');
    expect(rendered).toContain('INR');
    expect(rendered).not.toContain('$');
    // Digits only. toLocaleString follows the runtime locale, which groups this as 3,96,394 in
    // en-IN and 396,394 in en-US -- pinning either passes on one machine and fails on the other.
    expect(rendered.replace(/[^0-9]/g, '')).toBe('396394');
  });

  it('invents no symbol when the currency is unknown', () => {
    // A right number under a wrong unit is its own kind of wrong.
    const rendered = formatMoney(1500, null);
    expect(rendered).not.toContain('$');
    expect(rendered).not.toContain('INR');
    expect(rendered).toContain('1');
  });

  it('reports whether a figure is absent, separately from its value', () => {
    expect(isNotCosted(null)).toBe(true);
    expect(isNotCosted(undefined)).toBe(true);
    expect(isNotCosted(Number.NaN)).toBe(true);
    expect(isNotCosted(0)).toBe(false);
    expect(isNotCosted(396393.79)).toBe(false);
  });
});
