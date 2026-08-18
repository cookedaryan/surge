import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardTitle, Select, Slider, Button, StatTile, Skeleton } from '../../components/ui';
import { useJob, useRunOptimization } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { useJobProgress } from './useJobProgress';
import { useProjectData } from '../map/useProjectData';
import { api } from '../../lib/api';
import { RunProgress } from './RunProgress';
import {
  TERMINAL_STATUSES,
  parseSummary,
  CandidateComparison,
  FeederBreakdown,
  RepairDiagnosticsPanel,
  SummaryRow,
  ViolationList,
  unexplainedFailures
} from './resultParts';
import type { Job, JobDecisionSummary } from '../../lib/api';

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
  const resultJobId = useUiStore((s) => s.resultJobId);
  const setResultJobId = useUiStore((s) => s.setResultJobId);

  const [scenario, setScenario] = useState('Balanced');
  const [feederCapacityMw, setFeederCapacityMw] = useState(20.0);
  const [maxSpanMeters, setMaxSpanMeters] = useState(150);
  const [voltageKv, setVoltageKv] = useState(33.0);

  // Only the asset counts are needed here, and those are project-scoped. Passing the in-flight job
  // would fetch routes and poles for a run that has not produced any yet, on every run.
  const { counts, isLoading: assetsLoading } = useProjectData(currentProjectId, resultJobId);

  const runOptimization = useRunOptimization(currentProjectId);

  // The job itself is the source of truth for what to show, not component state. The sidebar
  // unmounts whichever pane is not active, so a run watched through local state would lose its
  // result the moment the operator looked at another tab — which, for a run measured in tens of
  // seconds, they will.
  const { data: job } = useJob(currentProjectId, currentJobId);
  const isSettled = !!job?.status && TERMINAL_STATUSES.includes(job.status);
  const progress = useJobProgress(currentProjectId, currentJobId, handleSettled);

  async function handleRun() {
    if (!currentProjectId) {
      showToast('Please select a project first.');
      return;
    }
    try {
      const queued = await runOptimization.mutateAsync({ scenario, feederCapacityMw, maxSpanMeters, voltageKv });
      setLiveBomOverride(null);
      setCurrentJobId(queued.id);
    } catch (err) {
      showToast('Could not queue optimization: ' + (err as Error).message, 'error');
    }
  }

  /** Publishes the finished run, then reports it — in that order. */
  async function handleSettled(settledJob: Job) {
    queryClient.invalidateQueries({ queryKey: ['job', currentProjectId, settledJob.id] });

    if (settledJob.status === 'FAILED') {
      showToast('Optimization failed: ' + (settledJob.errorMessage || 'unknown error'), 'error');
      return;
    }

    // Load the finished run's geometry into the cache *before* pointing the map at it.
    //
    // Switching first and invalidating afterwards does not work: the query for the new job does
    // not exist until the map has re-rendered, so there is nothing for the invalidation to
    // refetch. The map would mount the new key with no data, draw an empty result, and only fill
    // in once its own request came back — which is why the map went blank while the toast and the
    // decision card were already claiming success.
    const pid = currentProjectId as string;
    let loaded = true;
    await Promise.all([
      queryClient.fetchQuery({
        queryKey: ['routes', pid, settledJob.id],
        queryFn: () => api.getRoutesGeoJson(pid, settledJob.id)
      }),
      queryClient.fetchQuery({
        queryKey: ['poles', pid, settledJob.id],
        queryFn: () => api.getPolesGeoJson(pid, settledJob.id)
      }),
      queryClient.invalidateQueries({ queryKey: ['bom', pid] })
    ]).catch(() => {
      loaded = false;
    });

    setResultJobId(settledJob.id);

    // The run succeeded either way — the job is stored. Only the fetch failed, and saying
    // "completed cleanly" over a blank map is what makes that indistinguishable from a run that
    // produced nothing.
    if (loaded) {
      showToast('Optimization completed cleanly!', 'success');
    } else {
      showToast('Optimization finished, but its results could not be loaded. Reload to view them.', 'error');
    }
  }

  const isRunning = runOptimization.isPending || (!!currentJobId && !!job && !isSettled);
  const lastJob = isSettled ? job : null;
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
          <p className="text-sm text-textFaint m-0">Select a project to see its confirmed assets.</p>
        ) : assetsLoading ? (
          <div className="grid grid-cols-3 gap-2" aria-busy="true">
            {Array.from({ length: 5 }).map((_, i) => (
              <Skeleton key={i} className="h-[42px]" />
            ))}
          </div>
        ) : (
          <div className="grid grid-cols-3 gap-2">
            {[
              { label: 'WTGs', value: counts.wtgsOptimisable === counts.wtgsTotal ? counts.wtgsTotal : `${counts.wtgsOptimisable}/${counts.wtgsTotal}` },
              { label: 'Substations', value: counts.substations },
              { label: 'Roads', value: counts.referenceLines },
              { label: 'Parcels', value: counts.parcels },
              { label: 'Restricted', value: counts.restrictedAreas }
            ].map((m) => (
              <StatTile key={m.label} label={m.label} value={m.value} />
            ))}
          </div>
        )}
        {multipleSubstationsNote && <p className="text-sm text-textFaint mt-2 mb-0">ℹ️ {multipleSubstationsNote}</p>}
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
          <Button
            variant="primary"
            className="justify-center"
            loading={isRunning}
            disabled={!canRun}
            onClick={handleRun}
          >
            {isRunning ? 'Running…' : 'Run optimization pipeline'}
          </Button>
          {!isRunning && blockers.length > 0 && (
            <ul className="list-disc list-inside text-[11.5px] text-danger m-0">
              {blockers.map((b, i) => (
                <li key={i}>{b}</li>
              ))}
            </ul>
          )}
          {progress && isRunning && <RunProgress progress={progress} />}
        </div>
      </Card>
      {lastJob && !isRunning && (
        <JobResultCard job={lastJob} summary={summary} />
      )}
    </>
  );
}

function JobResultCard({ job, summary }: { job: Job; summary: JobDecisionSummary | null }) {
  const setResultsSheetOpen = useUiStore((s) => s.setResultsSheetOpen);

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
                {c.execution_failure?.details && (
                  <RepairDiagnosticsPanel details={c.execution_failure.details} />
                )}
              </div>
            ))}
          </div>
        )}
        {unexplainedFailures(summary).length > 0 && (
          <div className="mt-2 flex flex-col gap-1">
            {unexplainedFailures(summary).map((f, i) => (
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

  const recommendedMetrics = summary.candidates?.find(
    (c) => c.scenario_id === summary.recommendation?.recommended_scenario_id
  )?.engineering_metrics;

  return (
    <Card>
      <CardTitle
        aside={
          <button
            onClick={() => setResultsSheetOpen(true)}
            className="inline-flex items-center gap-1 rounded text-sm text-accent transition-colors duration-fast ease-out hover:text-accent400"
          >
            Expand
            <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round" strokeLinejoin="round">
              <path d="M15 3h6v6M14 10l7-7M9 21H3v-6M10 14l-7 7" />
            </svg>
          </button>
        }
      >
        Why This Route
      </CardTitle>
      <div className="flex flex-col gap-3 text-sm">
        {job.scenario && (
          <p className="text-sm text-textMuted m-0">
            Optimised for <span className="text-text font-semibold">{job.scenario}</span>
          </p>
        )}
        {summary.recommendation?.reason_details && summary.recommendation.reason_details.length > 0 ? (
          <div className="flex flex-col gap-2">
            {summary.recommendation.reason_details.map((rd, i) => (
              <div key={i} className="flex flex-col border-l-2 border-accent/40 pl-2">
                <span className="text-text font-medium text-[11.5px]">{rd.message}</span>
                {rd.metric && rd.candidate_value != null && rd.comparison_value != null && (
                  <span className="text-textFaint text-[10.5px]">
                    {rd.metric}: {rd.candidate_value.toFixed(2)} (baseline: {rd.comparison_value.toFixed(2)})
                  </span>
                )}
              </div>
            ))}
          </div>
        ) : reasons && reasons.length > 0 ? (
          <ul className="list-disc list-inside text-text">
            {reasons.map((r, i) => (
              <li key={i}>{r}</li>
            ))}
          </ul>
        ) : null}

        {ns && (
          <SummaryRow
            label="Network"
            items={[
              ['Feeders', ns.feeder_count],
              ['WTGs', ns.wtg_count],
              ['Segments', ns.segment_count],
              ['Length', `${(ns.total_route_length_m / 1000).toFixed(2)} km`],
              ...(recommendedMetrics?.total_traversal_cost != null
                ? ([['Traversal cost', recommendedMetrics.total_traversal_cost.toFixed(0)]] as [string, string | number][])
                : [])
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
              ['Soft crossing length', `${sc.soft_constraint_overlap_length_m.toFixed(0)} m`],
              ...(recommendedMetrics?.environmental_overlap_m2 != null
                ? ([['Environmental overlap', `${recommendedMetrics.environmental_overlap_m2.toFixed(0)} m²`]] as [string, string | number][])
                : [])
            ]}
            warn={sc.hard_exclusion_violation_count > 0}
          />
        )}

        {summary.violations && summary.violations.length > 0 && (
          <ViolationList violations={summary.violations} />
        )}

        {summary.feeders && summary.feeders.length > 0 && (
          <FeederBreakdown feeders={summary.feeders} />
        )}

        {summary.candidates && summary.candidates.length > 1 && (
          <CandidateComparison
            candidates={summary.candidates}
            recommendedId={summary.recommendation?.recommended_scenario_id}
          />
        )}
      </div>
    </Card>
  );
}

