import { describe, it, expect } from 'vitest';
import {
  asKm,
  asMoney,
  asMw,
  asPercent,
  asRatePerM2,
  isHighUtilisation,
  shown
} from './popupValues';

/**
 * Map popups used to fill missing values with invented ones: 3.0 MW for any turbine whose capacity
 * was never imported, 100 MW for any substation, $100/m² for any parcel with no rate, "Private
 * Owner" for any parcel with no owner. A popup stating a number is read as a fact about that asset,
 * so a plausible guess is worse than an admission — indistinguishable from surveyed data, and
 * exactly the figure someone repeats in a meeting.
 */

describe('shown', () => {
  it('renders a value that is present', () => {
    expect(shown(2.5, asMw)).toBe('2.5 MW');
    expect(shown('ACSR-PANTHER')).toBe('ACSR-PANTHER');
  });

  it('says Unknown rather than inventing a value', () => {
    expect(shown(null)).toContain('Unknown');
    expect(shown(undefined)).toContain('Unknown');
    expect(shown('')).toContain('Unknown');
  });

  it('marks an unknown value up so it cannot be mistaken for data', () => {
    // Styled quieter and italic; a bare "Unknown" in the same weight as a real figure reads as
    // a value in its own right.
    expect(shown(null)).toBe('<span class="popup-unknown">Unknown</span>');
  });

  it('renders a genuine zero as zero, not as a fallback', () => {
    // The regression this replaces: the old popups used `props.x || fallback`, so a real zero --
    // a parcel with no acquisition cost, a segment carrying no load -- displayed the invented
    // number instead. A zero is an answer.
    expect(shown(0, asMw)).toBe('0 MW');
    expect(shown(0, asMoney)).toBe('0');
    expect(shown(0)).toBe('0');
  });

  it('treats a non-finite number as unknown', () => {
    expect(shown(Number.NaN, asMw)).toContain('Unknown');
    expect(shown(Number.POSITIVE_INFINITY, asMoney)).toContain('Unknown');
  });

  it('formats numeric strings, which is how JSON money often arrives', () => {
    // BigDecimal fields serialise as strings often enough that a formatter has to cope.
    expect(shown('52.60', asPercent)).toBe('52.6%');
    expect(shown('1500', asMoney)).toBe('1,500');
  });

  it('passes through a non-numeric string rather than showing NaN', () => {
    expect(shown('n/a', asMoney)).toBe('n/a');
  });
});

describe('formatters', () => {
  it('renders kilometres from metres', () => {
    expect(asKm(4930.445)).toBe('4.93 km');
  });

  it('renders money grouped and rounded, in whatever locale is running', () => {
    // Deliberately not asserting where the separators fall. asMoney uses toLocaleString, which
    // follows the runtime locale: en-IN groups this as 55,99,319 (lakhs) and en-US as 5,599,319.
    // Pinning either would pass on one machine and fail on the other -- CI runs en-US, this
    // project's team does not.
    const rendered = asMoney(5599319.4);
    expect(rendered).toMatch(/[,.  ]/);
    expect(rendered.replace(/[^0-9]/g, '')).toBe('5599319');
  });

  it("labels money with the run's currency and invents none without it", () => {
    // The old formatter hardcoded "$" while the cost catalogue prices in INR, so every cost on
    // the map carried the wrong unit -- a right number under a wrong currency.
    expect(asMoney(1500, 'INR')).toContain('INR');
    expect(asMoney(1500, 'INR')).not.toContain('$');
    expect(asMoney(1500)).not.toContain('$');
    expect(asMoney(1500, null)).not.toContain('$');
  });

  it('renders a rate per square metre', () => {
    expect(asRatePerM2(100)).toBe('$100/m²');
  });
});

describe('isHighUtilisation', () => {
  it('flags a conductor running close to its effective ampacity', () => {
    // The reference project spans 15% to 90%. Only the percentage separates a comfortable choice
    // from a marginal one; the conductor type does not.
    expect(isHighUtilisation(90)).toBe(true);
    expect(isHighUtilisation(85)).toBe(true);
  });

  it('leaves a comfortable conductor unflagged', () => {
    expect(isHighUtilisation(15)).toBe(false);
    expect(isHighUtilisation(84.9)).toBe(false);
  });

  it('does not flag a conductor whose utilisation is unknown', () => {
    // An absent figure is not a warning; treating it as one would cry wolf on every older run.
    expect(isHighUtilisation(null)).toBe(false);
    expect(isHighUtilisation(undefined)).toBe(false);
  });

  it('accepts a numeric string', () => {
    expect(isHighUtilisation('90.00')).toBe(true);
  });
});
