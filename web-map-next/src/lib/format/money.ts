/**
 * Formatting money without inventing a unit or a value.
 *
 * <p>Costs used to be printed as `$${value ?? 0}`, which failed in two directions at once. The
 * fallback turned an unpriced network into a confident `$0.00` — a network nobody costed read as a
 * free one — and the symbol was hardcoded to dollars while the seeded catalogue prices in rupees.
 *
 * <p>Both come from the same habit of supplying something where the data says nothing.
 */

/** What a cost reads as when the run carried none. */
export const NOT_COSTED = 'Not costed';

/**
 * A money figure with its currency, or {@link NOT_COSTED}.
 *
 * <p>The currency is required to be explicit: passing a nullish currency yields an unprefixed number
 * rather than a guessed symbol, because a right number under a wrong unit is its own error.
 */
export function formatMoney(
  value: number | null | undefined,
  currency?: string | null
): string {
  if (value === null || value === undefined || Number.isNaN(value)) {
    return NOT_COSTED;
  }
  const amount = Math.round(value).toLocaleString();
  return currency ? `${currency} ${amount}` : amount;
}

/**
 * True when a run carries no cost at all.
 *
 * <p>Distinct from a cost of zero, which the engine cannot produce: it omits a component it could
 * not price rather than pricing it at zero.
 */
export function isNotCosted(value: number | null | undefined): boolean {
  return value === null || value === undefined || Number.isNaN(value);
}
