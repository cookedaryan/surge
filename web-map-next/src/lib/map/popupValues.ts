/**
 * Formatting for map popups, where a missing value must read as missing.
 *
 * <p>These popups used to fill gaps with invented figures: 3.0 MW for any turbine whose capacity was
 * never imported, 100 MW for any substation, $100/m² for any parcel with no rate, and "Private
 * Owner" for any parcel with no owner. A popup stating a specific number is read as a fact about
 * that asset, so a plausible guess is worse than an admission — it cannot be told apart from
 * surveyed data, and it is exactly the figure someone repeats in a meeting.
 */

const UNKNOWN_HTML = '<span class="popup-unknown">Unknown</span>';

/**
 * Renders a value, or says plainly that it is not known.
 *
 * <p>Deliberately a null/undefined check rather than a falsy check. The fallbacks this replaces used
 * `||`, so `0 || fallback` yielded the fallback: a genuine zero — a parcel with no acquisition cost,
 * a segment carrying no load — was displayed as the invented number rather than as zero.
 */
export function shown(value: unknown, format?: (v: number) => string): string {
  if (value === null || value === undefined || value === '') {
    return UNKNOWN_HTML;
  }
  if (typeof value === 'number') {
    if (!Number.isFinite(value)) {
      return UNKNOWN_HTML;
    }
    return format ? format(value) : String(value);
  }
  if (format) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? format(parsed) : String(value);
  }
  return String(value);
}

export const asMw = (v: number): string => `${v} MW`;
/**
 * Money with the currency the figure is actually in.
 *
 * <p>This hardcoded "$". The cost catalogue prices in INR, so every cost on the map was labelled in
 * the wrong unit — a right number under a wrong currency, which is its own kind of wrong. With no
 * currency known the number is shown unprefixed rather than under a guessed symbol.
 */
export const asMoney = (v: number, currency?: string | null): string => {
  const amount = Math.round(v).toLocaleString();
  return currency ? `${currency} ${amount}` : amount;
};
export const asPercent = (v: number): string => `${v}%`;
export const asKm = (v: number): string => `${(v / 1000).toFixed(2)} km`;
export const asRatePerM2 = (v: number): string => `$${v}/m²`;

/**
 * True when a conductor is close enough to its effective ampacity to be worth noticing.
 *
 * <p>The conductor type alone does not say whether the choice is comfortable or marginal, and a
 * segment at 90% is a different engineering proposition from one at 40%.
 */
export function isHighUtilisation(utilisationPct: unknown, threshold = 85): boolean {
  if (utilisationPct === null || utilisationPct === undefined) {
    return false;
  }
  const value = Number(utilisationPct);
  return Number.isFinite(value) && value >= threshold;
}
