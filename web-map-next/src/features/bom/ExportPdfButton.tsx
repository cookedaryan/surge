import { useState } from 'react';
import { Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { api } from '../../lib/api';

export function ExportPdfButton() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const showToast = useUiStore((s) => s.showToast);
  const [exporting, setExporting] = useState(false);

  async function handleExport() {
    if (!currentProjectId) return showToast('Please select a project first.');
    setExporting(true);
    try {
      await api.downloadPdfReport(currentProjectId);
    } catch (err) {
      showToast(`Export failed: ${(err as Error).message}`, 'error');
    } finally {
      setExporting(false);
    }
  }

  return (
    <Button size="sm" onClick={handleExport} disabled={exporting}>
      {exporting ? 'Exporting…' : 'Export PDF'}
    </Button>
  );
}
