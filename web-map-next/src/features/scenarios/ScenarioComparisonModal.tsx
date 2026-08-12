import { Dialog, Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { useScenarioComparison } from '../../lib/query';

const BADGE_COLORS: Record<string, string> = {
  'Minimum Cost': '#34D399',
  'Minimum Land Impact': '#8B5CF6',
  'Minimum Environmental Impact': '#06B6D4',
  Balanced: '#F5A524'
};

export function ScenarioComparisonModal() {
  const open = useUiStore((s) => s.scenarioComparisonOpen);
  const setOpen = useUiStore((s) => s.setScenarioComparisonOpen);
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const setRouteColorOverride = useUiStore((s) => s.setRouteColorOverride);
  const { data, isLoading, isError } = useScenarioComparison(currentProjectId, open);

  const scenarios = data?.scenarios ?? [];

  return (
    <Dialog open={open} onOpenChange={setOpen} title="Scenario Comparison" widthClassName="w-[760px]">
      {isLoading && <div className="text-[11px] text-textFaint">Loading scenario analytics…</div>}
      {isError && <div className="text-[11px] text-danger">Failed to load scenario comparison.</div>}
      {!isLoading && !isError && scenarios.length === 0 && (
        <div className="text-[11px] text-textFaint">No scenario comparison data available.</div>
      )}
      <div className="grid grid-cols-2 gap-3">
        {scenarios.map((sc) => {
          const color = BADGE_COLORS[sc.scenarioName] || '#4E8CFF';
          return (
            <div key={sc.scenarioName} className="border border-border rounded-md bg-surface2 p-3">
              <div className="flex items-center justify-between mb-2">
                <span className="text-xs font-semibold text-text">{sc.scenarioName}</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded" style={{ background: color, color: '#fff' }}>
                  {sc.scenarioName.split(' ')[0]}
                </span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5">
                <span>CAPEX</span>
                <span className="font-mono text-text tabular">${(sc.totalEstimatedCost || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5">
                <span>Losses</span>
                <span className="font-mono text-text tabular">{(sc.totalElectricalLossesKw || 0).toFixed(1)} kW</span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5">
                <span>ROW cost</span>
                <span className="font-mono text-text tabular">${(sc.landRowCompensationCost || 0).toLocaleString()}</span>
              </div>
              <div className="flex justify-between text-[11px] text-textMuted py-0.5 mb-2">
                <span>Length / Poles</span>
                <span className="font-mono text-text tabular">
                  {((sc.totalNetworkLengthMeters || 0) / 1000).toFixed(2)} km / {sc.totalPoles || 0}
                </span>
              </div>
              <Button
                size="sm"
                className="w-full justify-center"
                onClick={() => {
                  setRouteColorOverride(color);
                  setOpen(false);
                }}
              >
                Overlay Map Route
              </Button>
            </div>
          );
        })}
      </div>
    </Dialog>
  );
}
