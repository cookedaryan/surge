import { useState } from 'react';
import { Card, CardTitle, Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';
import { api } from '../../lib/api';
import { formatMoney } from '../../lib/format/money';
import { BomBoqTable } from './BomBoqTable';

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
    <div className="flex flex-col gap-3">
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

      {bom && (
        <div className="mb-4 space-y-1.5 text-sm bg-surface2 p-3 rounded-md border border-border">
          <div className="text-sm font-semibold uppercase text-textFaint mb-2">Lifecycle Cost Breakdown</div>
          <div className="flex justify-between">
            <span className="text-textFaint">Conductor CapEx</span>
            <span className="font-mono tabular">{formatMoney(bom.conductorCapex, bom.costCurrency)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-textFaint">Poles CapEx</span>
            <span className="font-mono tabular">{formatMoney(bom.poleCapex, bom.costCurrency)}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-textFaint">Land CapEx</span>
            <span className="font-mono tabular">{formatMoney(bom.landCapex, bom.costCurrency)}</span>
          </div>
          <div className="flex justify-between border-t border-border pt-1.5 mt-1.5">
            <span className="text-textFaint">Total CapEx</span>
            <span className="font-mono tabular">{formatMoney(bom.totalEstimatedCost, bom.costCurrency)}</span>
          </div>
          <div className="flex justify-between mt-3 pt-3 border-t border-border">
            <span className="text-textFaint">Present-value OpEx (Losses)</span>
            <span className="font-mono tabular">{formatMoney(bom.presentValueOpex, bom.costCurrency)}</span>
          </div>
          <div className="flex justify-between border-t border-border pt-1.5 mt-1.5 font-medium">
            <span>Lifecycle Cost</span>
            <span className="font-mono tabular">{formatMoney(bom.lifecycleCost, bom.costCurrency)}</span>
          </div>
        </div>
      )}

      <div className="flex gap-2">
        <Button size="sm" onClick={downloadCsv} disabled={exporting !== null} className="flex-1 justify-center">
          {exporting === 'csv' ? 'Exporting…' : 'Export CSV'}
        </Button>
        <Button size="sm" onClick={downloadPdf} disabled={exporting !== null} className="flex-1 justify-center">
          {exporting === 'pdf' ? 'Exporting…' : 'Export PDF'}
        </Button>
      </div>
    </Card>
    <BomBoqTable bom={bom} />
    </div>
  );
}
