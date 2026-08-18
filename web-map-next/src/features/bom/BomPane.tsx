import { useState } from 'react';
import { Card, CardTitle, Button, StatTile } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { useProjectData } from '../map/useProjectData';
import { api } from '../../lib/api';
import { formatMoney } from '../../lib/format/money';
import { BomBoqTable } from './BomBoqTable';
import { CostBreakdown } from './CostBreakdown';

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
        <StatTile label="Network length" value={`${lengthKm} km`} />
        <StatTile label="Poles" value={bom?.totalPoles ?? 0} />
        <StatTile label="Est. CapEx" value={cost} />
        <StatTile label="Losses" value={`${losses} kW`} />
      </div>

      {bom && (
        <div className="mb-4">
          <CostBreakdown bom={bom} />
        </div>
      )}

      <div className="flex gap-2">
        <Button size="sm" onClick={downloadCsv} loading={exporting === 'csv'} disabled={exporting !== null} className="flex-1 justify-center">
          Export CSV
        </Button>
        <Button size="sm" onClick={downloadPdf} loading={exporting === 'pdf'} disabled={exporting !== null} className="flex-1 justify-center">
          Export PDF
        </Button>
      </div>
    </Card>
    <BomBoqTable bom={bom} />
    </div>
  );
}
