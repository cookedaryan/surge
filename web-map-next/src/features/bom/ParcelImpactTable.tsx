import { useState } from 'react';
import type { ParcelImpactSummary } from '../../lib/api';

/** Shown before the list has to be asked for. Enough to read at a glance, not a wall. */
const INITIAL_ROWS = 12;

/** A parcel the route actually touches, by area or by a priced acquisition. */
export function isAffected(parcel: ParcelImpactSummary): boolean {
  return (parcel.affectedAreaM2 ?? 0) > 0 || parcel.selectedPresentValue != null;
}

/**
 * The parcels a route runs through.
 *
 * <p>The report returns every parcel imported for the project, not only the ones the network
 * touches — on a modest site that is sixty-odd rows of dashes under a heading promising impacts.
 * Only parcels with a recorded area or a priced acquisition are listed, and the number considered
 * is stated so a short list does not read as missing data.
 *
 * <p>When nothing is affected it says so rather than printing the whole cadastre. That case is
 * worth noticing on its own: a run with land CapEx but no parcel intersection means the land
 * figures came from the corridor rather than from the parcels, and the two are not the same claim.
 */
export function ParcelImpactTable({ parcels }: { parcels: ParcelImpactSummary[] }) {
  const [expanded, setExpanded] = useState(false);

  const affected = parcels.filter(isAffected);
  const considered = parcels.length;

  if (affected.length === 0) {
    return (
      <p className="m-0 rounded-md border border-border bg-surface2 px-2.5 py-2 text-sm text-textMuted">
        No parcel intersection was recorded for this run
        {considered > 0 ? ` (${considered} parcel${considered === 1 ? '' : 's'} considered)` : ''}. Any
        land cost shown above comes from the right-of-way corridor rather than from parcel geometry.
      </p>
    );
  }

  const rows = expanded ? affected : affected.slice(0, INITIAL_ROWS);

  return (
    <div>
      <div className="border border-border rounded-md overflow-x-auto">
        <table className="w-full text-left whitespace-nowrap">
          <thead className="bg-surface2 border-b border-border">
            <tr>
              <th className="px-2 py-1.5 font-medium text-textFaint">Parcel ID</th>
              <th className="px-2 py-1.5 font-medium text-textFaint">Owner</th>
              <th className="px-2 py-1.5 font-medium text-textFaint text-right">Affected area</th>
              <th className="px-2 py-1.5 font-medium text-textFaint">Instrument</th>
              <th className="px-2 py-1.5 font-medium text-textFaint text-right">Present Value</th>
              <th className="px-2 py-1.5 font-medium text-textFaint">Price Basis</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-border">
            {rows.map((parcel, idx) => (
              <tr key={parcel.parcelId || idx} className="bg-panel">
                <td className="px-2 py-1.5">{parcel.parcelId}</td>
                <td className="px-2 py-1.5">{parcel.ownerName || 'Unknown'}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular">
                  {parcel.affectedAreaM2 ? `${parcel.affectedAreaM2.toFixed(0)} m²` : '-'}
                </td>
                <td className="px-2 py-1.5">{parcel.transactionMode || '-'}</td>
                <td className="px-2 py-1.5 text-right font-mono tabular">
                  {parcel.selectedPresentValue != null
                    ? parcel.selectedPresentValue.toLocaleString(undefined, {
                        minimumFractionDigits: 2,
                        maximumFractionDigits: 2
                      })
                    : '-'}
                </td>
                <td className="px-2 py-1.5">{parcel.priceBasis || '-'}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      <div className="mt-1.5 flex items-baseline justify-between gap-2">
        <span className="text-xs text-textFaint">
          {affected.length} of {considered} parcels affected
        </span>
        {affected.length > INITIAL_ROWS && (
          <button
            onClick={() => setExpanded((v) => !v)}
            aria-expanded={expanded}
            className="text-xs text-accent transition-colors duration-fast ease-out hover:text-accent400"
          >
            {expanded ? 'Show fewer' : `Show all ${affected.length}`}
          </button>
        )}
      </div>
    </div>
  );
}
