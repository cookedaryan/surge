import { useState } from 'react';
import { Card, CardTitle, Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';
import { api } from '../../lib/api';
import { formatMoney } from '../../lib/format/money';

export function BomPane() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const showToast = useUiStore((s) => s.showToast);
  const { bom } = useProjectData(currentProjectId, currentJobId);

  const [exporting, setExporting] = useState<'csv' | 'pdf' | null>(null);

  async function runExport(kind: 'csv' | 'pdf', action: () => Promise<void>) {
    if (!currentProjectId) return showToast('Select a project first.');
    setExporting(kind);
    try {
      await action();
    } catch (err) {
      // A failed export used to be indistinguishable from a slow one: the click opened a blank
      // tab, the request was rejected, and nothing was ever said.
      showToast(`Export failed: ${(err as Error).message}`, 'error');
    } finally {
      setExporting(null);
    }
  }

  const downloadCsv = () =>
    runExport('csv', () => api.downloadBomCsv(currentProjectId as string, currentJobId));
  const downloadPdf = () =>
    runExport('pdf', () => api.downloadPdfReport(currentProjectId as string));

  const lengthKm = bom ? (bom.totalNetworkLengthMeters / 1000).toFixed(2) : '0.00';
  // Was `?? '$0.00'`, which reported a network nobody had priced as a free one, in a currency the
  // catalogue does not use.
  const cost = formatMoney(bom?.totalEstimatedCost, bom?.costCurrency);
  const losses = bom?.totalElectricalLossesKw?.toFixed(2) ?? '0.00';

  return (
    <Card>
      <CardTitle>Bill of Materials</CardTitle>
      <div className="grid grid-cols-2 gap-2 mb-3">
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{lengthKm} km</div>
          <div className="text-[11.5px] text-textFaint mt-1">Network length</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{bom?.totalPoles ?? 0}</div>
          <div className="text-[11.5px] text-textFaint mt-1">Poles</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{cost}</div>
          <div className="text-[11.5px] text-textFaint mt-1">Est. CapEx</div>
        </div>
        <div className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
          <div className="font-mono text-[17px] font-semibold tabular leading-none">{losses} kW</div>
          <div className="text-[11.5px] text-textFaint mt-1">Losses</div>
        </div>
      </div>
      <div className="flex gap-2">
        <Button size="sm" onClick={downloadCsv} disabled={exporting !== null} className="flex-1 justify-center">
          {exporting === 'csv' ? 'Exporting…' : 'Export CSV'}
        </Button>
        <Button size="sm" onClick={downloadPdf} disabled={exporting !== null} className="flex-1 justify-center">
          {exporting === 'pdf' ? 'Exporting…' : 'Export PDF'}
        </Button>
      </div>
    </Card>
  );
}
