import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardTitle, Select, Slider, Button } from '../../components/ui';
import { useRunOptimization } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { useJobProgress } from './useJobProgress';
import { useProjectData } from '../map/useProjectData';
import type { Job, JobDecisionSummary } from '../../lib/api';

const SCENARIOS = [
  { value: 'Balanced', label: 'Balanced (cost + environment)' },
  { value: 'Minimum Cost', label: 'Minimum Cost' },
  { value: 'Minimum Land Impact', label: 'Minimum Land Impact' },
  { value: 'Minimum Environmental Impact', label: 'Minimum Environmental Impact' }
];

function parseSummary(job: Job | null): JobDecisionSummary | null {
  if (!job?.resultSummaryJson) return null;
  try {
    return JSON.parse(job.resultSummaryJson) as JobDecisionSummary;
  } catch {
    return null;
  }
}

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
  const [lastJob, setLastJob] = useState<Job | null>(null);

  const { counts, isLoading: assetsLoading } = useProjectData(currentProjectId, currentJobId);

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
      setLastJob(job);
      queryClient.invalidateQueries({ queryKey: ['routes', currentProjectId] });
      queryClient.invalidateQueries({ queryKey: ['poles', currentProjectId] });
      queryClient.invalidateQueries({ queryKey: ['bom', currentProjectId] });
      setLiveBomOverride(null);
      if (job.status === 'FAILED') {
        showToast('Optimization failed: ' + (job.errorMessage || 'unknown error'), 'error');
      } else {
        showToast('Optimization completed cleanly!', 'success');
      }
    } catch (err) {
      showToast('Optimization failed: ' + (err as Error).message, 'error');
      setLastJob(null);
    }
  }

  const isRunning = runOptimization.isPending;
  const summary = parseSummary(lastJob);

  const blockers: string[] = [];
  if (!currentProjectId) {
    blockers.push('Select a project first.');
  } else if (!assetsLoading) {
    if (counts.wtgsOptimisable === 0) {
      blockers.push(
        counts.wtgsTotal === 0
          ? 'No WTGs imported for this project.'
          : `All ${counts.wtgsTotal} imported WTG(s) are excluded by status (cancelled/low-AEP/to-be-shifted) — none are optimisable.`
      );
    }
    if (counts.substations === 0) {
      blockers.push('No substation imported for this project.');
    }
  }
  const canRun = blockers.length === 0 && !assetsLoading;
  const multipleSubstationsNote =
    currentProjectId && !assetsLoading && counts.substations > 1
      ? `${counts.substations} substations found — the one nearest the WTG cluster will be used automatically.`
      : null;

  return (
    <>
      <Card>
        <CardTitle>Confirmed Assets</CardTitle>
        {!currentProjectId ? (
          <p className="text-[11.5px] text-textFaint m-0">Select a project to see its confirmed assets.</p>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'WTGs', value: counts.wtgsOptimisable === counts.wtgsTotal ? counts.wtgsTotal : `${counts.wtgsOptimisable}/${counts.wtgsTotal}` },
              { label: 'Substations', value: counts.substations },
              { label: 'Roads', value: counts.referenceLines },
              { label: 'Parcels', value: counts.parcels },
              { label: 'Restricted', value: counts.restrictedAreas }
            ].map((m) => (
              <div key={m.label} className="border border-border rounded-md bg-surface2 px-2 pt-2 pb-1.5">
                <div className="font-mono text-[13.5px] font-semibold tabular leading-none">{m.value}</div>
                <div className="text-[11.5px] text-textFaint mt-1">{m.label}</div>
              </div>
            ))}
          </div>
        )}
        {multipleSubstationsNote && <p className="text-[11.5px] text-textFaint mt-2 mb-0">ℹ️ {multipleSubstationsNote}</p>}
      </Card>
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
          <Button variant="primary" className="justify-center" disabled={isRunning || !canRun} onClick={handleRun}>
            {isRunning ? 'Running…' : 'Run optimization pipeline'}
          </Button>
          {!isRunning && blockers.length > 0 && (
            <ul className="list-disc list-inside text-[11.5px] text-danger m-0">
              {blockers.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          )}
          {progress && isRunning && (
            <div className="mt-1">
              <div className="h-1.5 rounded-full bg-surface2 overflow-hidden">
                <div
                  className={`h-full rounded-full transition-all ${progress.status === 'FAILED' ? 'bg-danger' : 'bg-accent'}`}
                  style={{ width: `${progress.progressPercent ?? 10}%` }}
                />
              </div>
              <p className="text-[11.5px] text-textFaint mt-1.5">{progress.message}</p>
            </div>
          )}
        </div>
      </Card>
      {lastJob && !isRunning && (
        <JobResultCard job={lastJob} summary={summary} />
      )}
    </>
  );
}

function JobResultCard({ job, summary }: { job: Job; summary: JobDecisionSummary | null }) {
  if (job.status === 'FAILED') {
    return (
      <Card className="border-danger/60 bg-danger/5">
        <CardTitle>Optimization Failed</CardTitle>
        <p className="text-[11.5px] text-danger font-medium mb-2">{job.errorMessage || 'No feasible route was found.'}</p>
        {summary?.candidates && summary.candidates.length > 0 && (
          <div className="flex flex-col gap-1.5">
            <p className="text-[11.5px] text-textMuted uppercase tracking-wide font-bold">Candidate scenarios evaluated</p>
            {summary.candidates.map((c) => (
              <div key={c.scenario_id} className="text-[11.5px] text-text border-b border-border last:border-b-0 py-1">
                <span className="font-mono">{c.scenario_id}</span>
                {c.strategy ? <span className="text-textFaint"> ({c.strategy})</span> : null}
                {c.disqualifications && c.disqualifications.length > 0 && (
                  <ul className="list-disc list-inside text-textFaint mt-0.5">
                    {c.disqualifications.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                )}
              </div>
            ))}
          </div>
        )}
        {summary?.failures && summary.failures.length > 0 && (
          <div className="mt-2 flex flex-col gap-1">
            {summary.failures.map((f, i) => (
              <p key={i} className="text-[11.5px] text-textFaint">
                <span className="font-mono text-textMuted">{f.stage}</span>: {f.message}
              </p>
            ))}
          </div>
        )}
      </Card>
    );
  }

  if (!summary) return null;

  const es = summary.electricalSummary;
  const ns = summary.networkSummary;
  const ps = summary.poleSummary;
  const sc = summary.spatialConstraintSummary;
  const reasons = summary.recommendation?.reasons;

  return (
    <Card>
      <CardTitle>Why This Route</CardTitle>
      <div className="flex flex-col gap-3 text-[11.5px]">
        {job.scenario && (
          <p className="text-[11.5px] text-textMuted m-0">
            Optimised for <span className="text-text font-semibold">{job.scenario}</span>
          </p>
        )}
        {reasons && reasons.length > 0 && (
          <ul className="list-disc list-inside text-text">
            {reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        )}

        {ns && (
          <SummaryRow
            label="Network"
            items={[
              ['Feeders', ns.feeder_count],
              ['WTGs', ns.wtg_count],
              ['Segments', ns.segment_count],
              ['Length', `${(ns.total_route_length_m / 1000).toFixed(2)} km`]
            ]}
          />
        )}

        {es && (
          <SummaryRow
            label="Electrical"
            items={[
              ['Converged', es.converged ? 'yes' : 'no'],
              ['Valid', es.valid ? 'yes' : 'no'],
              ['Max loading', es.maximum_loading_percent != null ? `${es.maximum_loading_percent.toFixed(1)}%` : '—'],
              [
                'Voltage range',
                es.minimum_voltage_pu != null && es.maximum_voltage_pu != null
                  ? `${es.minimum_voltage_pu.toFixed(3)}–${es.maximum_voltage_pu.toFixed(3)} pu`
                  : '—'
              ],
              ['Active losses', es.total_active_loss_mw != null ? `${(es.total_active_loss_mw * 1000).toFixed(1)} kW` : '—']
            ]}
            warn={!es.converged || !es.valid}
          />
        )}

        {ps && (
          <SummaryRow
            label="Poles"
            items={[
              ['Total', ps.total_poles],
              ['Terminal', ps.terminal_poles],
              ['Angle', ps.angle_poles],
              ['Intermediate', ps.intermediate_poles],
              ['Junction', ps.junction_poles]
            ]}
          />
        )}

        {sc && (
          <SummaryRow
            label="Land & Constraints"
            items={[
              ['Hard exclusion violations', sc.hard_exclusion_violation_count],
              ['Road/HT-line crossings', sc.road_crossing_count],
              ['Affected parcels', sc.affected_parcel_count],
              ['Soft crossing length', `${sc.soft_constraint_overlap_length_m.toFixed(0)} m`]
            ]}
            warn={sc.hard_exclusion_violation_count > 0}
          />
        )}
      </div>
    </Card>
  );
}

function SummaryRow({
  label,
  items,
  warn
}: {
  label: string;
  items: [string, string | number][];
  warn?: boolean;
}) {
  return (
    <div>
      <p className={`text-[11.5px] uppercase tracking-wide font-bold mb-1 ${warn ? 'text-danger' : 'text-textMuted'}`}>
        {label}
      </p>
      <div className="grid grid-cols-2 gap-x-3 gap-y-0.5">
        {items.map(([k, v]) => (
          <div key={k} className="flex justify-between gap-2">
            <span className="text-textFaint">{k}</span>
            <span className="font-mono text-text tabular">{v}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
