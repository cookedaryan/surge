import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';

export function BomStrip() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const liveOverride = useUiStore((s) => s.liveBomOverride);
  const { bom } = useProjectData(currentProjectId, currentJobId);

  const lengthKm = liveOverride ? liveOverride.lengthKm : bom ? (bom.totalNetworkLengthMeters / 1000).toFixed(2) : '0.00';
  const poles = liveOverride ? liveOverride.poles : bom?.totalPoles ?? 0;
  const cost = liveOverride ? liveOverride.cost : bom?.totalEstimatedCost ?? 0;
  const losses = bom?.totalElectricalLossesKw ?? 0;

  const segments = [
    { label: 'Network length', value: `${lengthKm} km` },
    { label: 'Poles', value: String(poles) },
    { label: 'Est. CapEx', value: `$${cost.toLocaleString()}` },
    { label: 'Losses', value: `${losses.toFixed(2)} kW` }
  ];

  return (
    <div className="absolute left-3.5 bottom-3.5 flex rounded-lg overflow-hidden font-ui">
      {segments.map((seg, i) => (
        <div
          key={seg.label}
          className={`bg-panel border border-borderStrong px-4 py-2.5 flex flex-col gap-0.5 min-w-[88px] ${i > 0 ? 'border-l-0' : ''}`}
        >
          <span className="font-mono font-bold text-[13.5px] tabular">{seg.value}</span>
          <span className="text-[9.5px] uppercase tracking-wide text-textFaint">{seg.label}</span>
        </div>
      ))}
    </div>
  );
}
