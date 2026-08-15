import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';
import { Card, CardTitle } from '../../components/ui';

export function AssetSummary() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const { counts } = useProjectData(currentProjectId, currentJobId);

  const metrics = [
    { label: 'WTGs', value: counts.wtgsOptimisable === counts.wtgsTotal ? counts.wtgsTotal : `${counts.wtgsOptimisable}/${counts.wtgsTotal}` },
    { label: 'Substations', value: counts.substations },
    { label: 'Towers', value: counts.towers },
    { label: 'Ref. lines', value: counts.referenceLines },
    { label: 'Parcels', value: counts.parcels },
    { label: 'Restricted', value: counts.restrictedAreas }
  ];

  return (
    <Card>
      <CardTitle>Project Asset Summary</CardTitle>
      <div className="grid grid-cols-3 gap-2">
        {metrics.map((m) => (
          <div key={m.label} className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
            <div className="font-mono text-[17px] font-semibold tabular leading-none">{m.value}</div>
            <div className="text-[11.5px] text-textFaint mt-1">{m.label}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
