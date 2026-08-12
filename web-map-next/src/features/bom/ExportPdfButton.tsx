import { Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';
import { api } from '../../lib/api';

export function ExportPdfButton() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const showToast = useUiStore((s) => s.showToast);

  return (
    <Button
      size="sm"
      onClick={() => {
        if (!currentProjectId) return showToast('Please select a project first.');
        window.open(api.getPdfReportUrl(currentProjectId), '_blank');
      }}
    >
      Export PDF
    </Button>
  );
}
