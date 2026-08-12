import { Button } from '../../components/ui';
import { useUiStore } from '../../lib/store';

export function CompareScenariosButton() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const showToast = useUiStore((s) => s.showToast);
  const setOpen = useUiStore((s) => s.setScenarioComparisonOpen);

  return (
    <Button
      size="sm"
      onClick={() => {
        if (!currentProjectId) return showToast('Please select a project first.');
        setOpen(true);
      }}
    >
      Compare Scenarios
    </Button>
  );
}
