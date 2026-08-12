import { Card, CardTitle, Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';
import { api } from '../../lib/api';

export function BomPane() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const showToast = useUiStore((s) => s.showToast);
  const { bom } = useProjectData(currentProjectId, currentJobId);

  function downloadCsv() {
    if (!currentProjectId) return showToast('Select a project first.');
    window.open(api.getBomCsvUrl(currentProjectId, currentJobId), '_blank');
  }
  function downloadPdf() {
    if (!currentProjectId) return showToast('Select a project first.');
    window.open(api.getPdfReportUrl(currentProjectId), '_blank');
  }

  const lengthKm = bom ? (bom.totalNetworkLengthMeters / 1000).toFixed(2) : '0.00';
  const cost = bom?.totalEstimatedCost?.toLocaleString('en-US', { style: 'currency', currency: 'USD' }) ?? '$0.00';
  const losses = bom?.totalElectricalLossesKw?.toFixed(2) ?? '0.00';

  return (
    <Card>
      <CardTitle>Bill of Materials</CardTitle>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{lengthKm} km</div>
          <div className="text-[10px] text-textFaint mt-1">Network length</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{bom?.totalPoles ?? 0}</div>
          <div className="text-[10px] text-textFaint mt-1">Poles</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{cost}</div>
          <div className="text-[10px] text-textFaint mt-1">Est. CapEx</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{losses} kW</div>
          <div className="text-[10px] text-textFaint mt-1">Losses</div>
        </div>
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={downloadCsv} className="flex-1 justify-center">Export CSV</Button>
        <Button size="sm" onClick={downloadPdf} className="flex-1 justify-center">Export PDF</Button>
      </div>
    </Card>
  );
}
