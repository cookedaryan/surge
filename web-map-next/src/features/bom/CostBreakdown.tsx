import { formatMoney, isNotCosted } from '../../lib/format/money';
import type { BomReport } from '../../lib/api';

function Row({
  label,
  value,
  currency,
  strong,
  divider
}: {
  label: string;
  value: number | null | undefined;
  currency?: string | null;
  strong?: boolean;
  divider?: boolean;
}) {
  return (
    <div className={`flex justify-between gap-3 ${divider ? 'border-t border-border pt-1.5 mt-1.5' : ''} ${strong ? 'font-medium' : ''}`}>
      <span className={strong ? 'text-text' : 'text-textFaint'}>{label}</span>
      <span className={`font-mono tabular ${isNotCosted(value) ? 'italic text-textFaint' : 'text-text'}`}>
        {formatMoney(value, currency)}
      </span>
    </div>
  );
}

/**
 * What the network costs, and over what horizon.
 *
 * <p>Shared by the BOM pane and the run breakdown so the two cannot disagree about the same run.
 *
 * <p>An uncosted component reads as "Not costed" rather than as zero, because the engine omits what
 * it cannot price instead of pricing it at nothing — a distinction that decides whether a total is
 * a quote or a partial sum.
 */
export function CostBreakdown({ bom }: { bom: BomReport }) {
  const partial = (bom.costFailureCount ?? 0) > 0;

  return (
    <div className="space-y-1.5 rounded-md border border-border bg-surface2 p-3 text-sm">
      <Row label="Conductor CapEx" value={bom.conductorCapex} currency={bom.costCurrency} />
      <Row label="Poles CapEx" value={bom.poleCapex} currency={bom.costCurrency} />
      <Row label="Land CapEx" value={bom.landCapex} currency={bom.costCurrency} />
      <Row label="Total CapEx" value={bom.totalEstimatedCost} currency={bom.costCurrency} divider strong />

      <div className="mt-3 pt-3 border-t border-border space-y-1.5">
        <Row label="Present-value OpEx (losses)" value={bom.presentValueOpex} currency={bom.costCurrency} />
        {bom.annualLossEnergyMwh != null && (
          <div className="flex justify-between gap-3">
            <span className="text-textFaint">Annual loss energy</span>
            <span className="font-mono tabular text-text">{bom.annualLossEnergyMwh.toFixed(1)} MWh</span>
          </div>
        )}
        <Row label="Annual loss cost" value={bom.annualLossCost} currency={bom.costCurrency} />
        <Row label="Lifecycle cost" value={bom.lifecycleCost} currency={bom.costCurrency} divider strong />
      </div>

      {partial && (
        // The type documents this explicitly: above zero, the total is a partial sum. Left unsaid,
        // a figure short by an unpriced component is indistinguishable from a complete one.
        <p role="status" className="m-0 mt-3 flex items-start gap-1.5 border-t border-border pt-2.5 text-xs text-warning">
          <svg viewBox="0 0 24 24" className="mt-px h-3.5 w-3.5 flex-none" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <path d="M12 9v4m0 3.5h.01M10.3 3.9 1.8 18a2 2 0 0 0 1.7 3h17a2 2 0 0 0 1.7-3L13.7 3.9a2 2 0 0 0-3.4 0z" />
          </svg>
          <span>
            {bom.costFailureCount} component{bom.costFailureCount === 1 ? '' : 's'} could not be
            priced, so these totals are a partial sum rather than a full cost.
          </span>
        </p>
      )}
    </div>
  );
}
