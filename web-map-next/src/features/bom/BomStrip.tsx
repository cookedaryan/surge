import { useUiStore } from '../../lib/store';
import { formatMoney } from '../../lib/format/money';
import { useProjectData } from '../map/useProjectData';

export function BomStrip() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const resultJobId = useUiStore((s) => s.resultJobId);
  const liveOverride = useUiStore((s) => s.liveBomOverride);
  const activeSidebarTab = useUiStore((s) => s.activeSidebarTab);
  const { bom } = useProjectData(currentProjectId, resultJobId);

  // The BOM pane shows these same four figures, larger and with the exports beside them. Repeating
  // them over the map while it is open costs map area and says nothing new.
  if (activeSidebarTab === 'bom') return null;

  const lengthKm = liveOverride ? liveOverride.lengthKm : bom ? (bom.totalNetworkLengthMeters / 1000).toFixed(2) : '0.00';
  const poles = liveOverride ? liveOverride.poles : bom?.totalPoles ?? 0;
  const cost = liveOverride ? liveOverride.cost : bom?.totalEstimatedCost ?? null;
  const losses = bom?.totalElectricalLossesKw ?? 0;

  const segments = [
    { label: 'Network length', value: `${lengthKm} km` },
    { label: 'Poles', value: String(poles) },
    // No `$` and no zero default: the figure carries the catalogue's own currency, and a run with
    // no catalogue reads as not costed rather than as costing nothing.
    { label: 'Est. CapEx', value: formatMoney(cost, bom?.costCurrency) },
    { label: 'Losses', value: `${losses.toFixed(2)} kW` }
  ];

  return (
    <div className="absolute left-3.5 bottom-3.5 z-[1010] flex rounded-lg overflow-hidden font-ui">
      {segments.map((seg, i) => (
        <div
          key={seg.label}
          className={`bg-panel border border-borderStrong px-4 py-2.5 flex flex-col gap-0.5 min-w-[88px] ${i > 0 ? 'border-l-0' : ''}`}
        >
          <span className="font-mono font-bold text-[13.5px] tabular">{seg.value}</span>
          <span className="text-[11.5px] uppercase tracking-wide text-textFaint">{seg.label}</span>
        </div>
      ))}
    </div>
  );
}
