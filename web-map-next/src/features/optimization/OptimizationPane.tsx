import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardTitle, Select, Slider, Button } from '../../components/ui';
import { useRunOptimization } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { useJobProgress } from './useJobProgress';

const SCENARIOS = [
  { value: 'Balanced', label: 'Balanced (cost + environment)' },
  { value: 'Minimum Cost', label: 'Minimum Cost' },
  { value: 'Minimum Land Impact', label: 'Minimum Land Impact' },
  { value: 'Minimum Environmental Impact', label: 'Minimum Environmental Impact' }
];

export function OptimizationPane() {
  const queryClient = useQueryClient();
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const setCurrentJobId = useUiStore((s) => s.setCurrentJobId);
  const showToast = useUiStore((s) => s.showToast);
  const setLiveBomOverride = useUiStore((s) => s.setLiveBomOverride);

  const [scenario, setScenario] = useState('Balanced');
  const [feederCapacityMw, setFeederCapacityMw] = useState(20.0);
  const [maxSpanMeters, setMaxSpanMeters] = useState(150);
  const [voltageKv, setVoltageKv] = useState(33.0);

  const runOptimization = useRunOptimization(currentProjectId);
  // The backend runs the pipeline synchronously within the POST /jobs request, so by the
  // time it resolves below the job (and its progress stream) is already finished — the SSE
  // subscription this opens almost never observes a live "completed" event. It's kept for the
  // rare case progress messages do arrive, but nothing here is depended on for correctness.
  const progress = useJobProgress(currentProjectId, currentJobId, () => {});

  async function handleRun() {
    if (!currentProjectId) {
      showToast('Please select a project first.');
      return;
    }
    try {
      const job = await runOptimization.mutateAsync({ scenario, feederCapacityMw, maxSpanMeters, voltageKv });
      setCurrentJobId(job.id);
      queryClient.invalidateQueries({ queryKey: ['routes', currentProjectId] });
      queryClient.invalidateQueries({ queryKey: ['poles', currentProjectId] });
      queryClient.invalidateQueries({ queryKey: ['bom', currentProjectId] });
      setLiveBomOverride(null);
      if (job.status === 'FAILED') {
        showToast('Optimization failed: ' + (job.errorMessage || 'unknown error'));
      } else {
        showToast('Optimization completed cleanly!');
      }
    } catch (err) {
      showToast('Optimization failed: ' + (err as Error).message);
    }
  }

  const isRunning = runOptimization.isPending;

  return (
    <Card>
      <CardTitle>Scenario &amp; Algorithm</CardTitle>
      <div className="flex flex-col gap-3">
        <div>
          <label className="block text-[11.5px] text-textMuted mb-1.5">Optimization scenario</label>
          <Select value={scenario} onValueChange={setScenario} options={SCENARIOS} className="w-full" />
        </div>
        <div>
          <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
            Feeder capacity <span className="font-mono text-text tabular">{feederCapacityMw.toFixed(1)} MW</span>
          </label>
          <Slider value={feederCapacityMw} onValueChange={setFeederCapacityMw} min={5} max={50} step={1} />
        </div>
        <div>
          <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
            Max pole span <span className="font-mono text-text tabular">{maxSpanMeters.toFixed(0)} m</span>
          </label>
          <Slider value={maxSpanMeters} onValueChange={setMaxSpanMeters} min={50} max={300} step={10} />
        </div>
        <div>
          <label className="flex justify-between text-[11.5px] text-textMuted mb-1.5">
            System voltage <span className="font-mono text-text tabular">{voltageKv.toFixed(1)} kV</span>
          </label>
          <Slider value={voltageKv} onValueChange={setVoltageKv} min={11} max={132} step={11} />
        </div>
        <Button variant="primary" className="justify-center" disabled={isRunning || runOptimization.isPending} onClick={handleRun}>
          {isRunning ? 'Running…' : 'Run optimization pipeline'}
        </Button>
        {progress && isRunning && (
          <div className="mt-1">
            <div className="h-1.5 rounded-full bg-surface2 overflow-hidden">
              <div
                className={`h-full rounded-full transition-all ${progress.status === 'FAILED' ? 'bg-danger' : 'bg-accent'}`}
                style={{ width: `${progress.progressPercent ?? 10}%` }}
              />
            </div>
            <p className="text-[11px] text-textFaint mt-1.5">{progress.message}</p>
          </div>
        )}
      </div>
    </Card>
  );
}
