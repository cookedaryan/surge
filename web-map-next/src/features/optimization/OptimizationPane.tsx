import { useState } from 'react';
import { useQueryClient } from '@tanstack/react-query';
import { Card, CardTitle, Select, Slider, Button } from '../../components/ui';
import { useJob, useRunOptimization } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { useJobProgress } from './useJobProgress';
import { useProjectData } from '../map/useProjectData';
import { api } from '../../lib/api';
import type {
  CandidateSummary,
  ElectricalViolation,
  FeederElectricalResult,
  Job,
  JobDecisionSummary,
  RepairDiagnostics
} from '../../lib/api';

/** Statuses after which a job will not change again. */
const TERMINAL_STATUSES = ['COMPLETED', 'FAILED', 'CANCELLED'];

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

/**
 * What the recommendation beat, and on what figures.
 *
 * <p>The alternatives used to appear only when a run failed — precisely the wrong way round. A
 * successful run is when an engineer asks what else was on the table: the reference project's
 * third candidate routes 136 km against the winner's 70 km, and a recommendation you cannot
 * see the competition for is a recommendation you have to take on trust.
 *
 * <p>Absolute values, not deltas. The engine's own signed comparisons need per-metric knowledge of
 * which direction is better (shorter route: good; more poles: usually worse), and presenting them
 * as improvements would mean asserting a direction this component does not know.
 */
function CandidateComparison({
  candidates,
  recommendedId
}: {
  candidates: CandidateSummary[];
  recommendedId?: string | null;
}) {
  const [open, setOpen] = useState(false);
  const ordered = [...candidates].sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));
  const rejected = candidates.filter((c) => c.eligible === false).length;

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className="flex w-full items-center justify-between gap-2 text-[11.5px] uppercase tracking-wide font-bold mb-1 text-textMuted"
      >
        <span>
          Alternatives considered ({candidates.length})
          {rejected > 0 && ` — ${rejected} ineligible`}
        </span>
        <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="flex flex-col gap-1">
          <div className="grid grid-cols-6 gap-x-2 text-[11px] uppercase tracking-wide text-textFaint">
            <span>Scenario</span>
            <span className="text-right">Score</span>
            <span className="text-right">Length</span>
            <span className="text-right">Losses</span>
            <span className="text-right">Poles</span>
            <span className="text-right">Load</span>
          </div>
          {ordered.map((c) => {
            const m = c.engineering_metrics;
            const isRecommended = recommendedId != null && c.scenario_id === recommendedId;
            return (
              <div key={c.scenario_id} className="border-b border-border last:border-b-0 pb-1 last:pb-0">
                <div
                  className={`grid grid-cols-6 gap-x-2 text-[11.5px] font-mono tabular ${
                    isRecommended ? 'text-accent font-semibold' : 'text-text'
                  }`}
                >
                  <span className="font-ui">
                    {c.scenario_id}
                    {isRecommended && <span title="Recommended"> ★</span>}
                  </span>
                  <span className="text-right">
                    {c.total_benefit_score != null ? c.total_benefit_score.toFixed(3) : '—'}
                  </span>
                  <span className="text-right">
                    {m?.total_route_length_m != null ? `${(m.total_route_length_m / 1000).toFixed(1)} km` : '—'}
                  </span>
                  <span className="text-right">
                    {m?.total_active_loss_mw != null ? `${(m.total_active_loss_mw * 1000).toFixed(0)} kW` : '—'}
                  </span>
                  <span className="text-right">{m?.physical_pole_count ?? '—'}</span>
                  <span className="text-right">
                    {m?.maximum_loading_percent != null ? `${m.maximum_loading_percent.toFixed(1)}%` : '—'}
                  </span>
                </div>
                <p className="text-[11px] text-textFaint m-0 mt-0.5">
                  {c.strategy ? c.strategy.replace(/_/g, ' ') : 'unnamed strategy'}
                  {c.electrical_status === 'INVALID' && (
                    <span className="text-danger"> · electrically invalid</span>
                  )}
                </p>
                {c.disqualifications && c.disqualifications.length > 0 && (
                  <ul className="list-disc list-inside text-[11px] text-danger m-0 mt-0.5">
                    {c.disqualifications.map((reason, i) => (
                      <li key={i}>{reason}</li>
                    ))}
                  </ul>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}

/**
 * A measured value at the precision the engine reports it, not at full float width.
 *
 * <p>Voltages arrive as 1.0599745548368775 and loadings as 93.15750540268613. Four decimals matches
 * what the engine's own violation messages print, and trailing zeros are dropped so a current of
 * 1880 does not read as 1880.0000.
 */
function measure(value: number): string {
  return String(Number(value.toFixed(4)));
}

/**
 * Failures whose message is not already shown against a candidate.
 *
 * <p>Every candidate that fails electrical validation produces both an `execution_failure` and an
 * entry in `failures`, carrying the same sentence. Rendering both repeats each failure twice — and
 * with three candidates the card became the same paragraph six times over.
 */
function unexplainedFailures(summary: JobDecisionSummary | null) {
  const failures = summary?.failures ?? [];
  const shown = new Set(
    (summary?.candidates ?? [])
      .map((c) => c.execution_failure?.message ?? c.execution_failure?.details?.summary)
      .filter((m): m is string => !!m)
  );
  return failures.filter((f) => !shown.has(f.message));
}

/**
 * Why electrical repair gave up, in the terms an engineer can act on.
 *
 * <p>A failed run used to say `REPAIR_EXHAUSTED` and stop, which cannot distinguish a catalogue
 * that is too small from a design no conductor will fix. Python has reported the difference since
 * `710f75f`; this is where it becomes visible.
 */
function RepairDiagnosticsPanel({ details }: { details: RepairDiagnostics }) {
  const unresolved = details.unresolved_violations ?? [];
  const attempts = details.repair_attempts ?? [];
  const largest = details.largest_cable_available;

  return (
    <div className="mt-1 flex flex-col gap-1.5 border-l-2 border-danger/40 pl-2">
      {unresolved.length > 0 && (
        <div>
          <p className="text-[11px] uppercase tracking-wide text-textMuted m-0 mb-0.5">
            Unresolved ({unresolved.length})
          </p>
          <ul className="m-0 list-none p-0">
            {unresolved.map((v, i) => (
              <li key={`${v.code}-${i}`} className="text-[11px] text-text">
                <span className="font-mono text-textMuted">{v.node_id || v.segment_id || v.feeder_id}</span>{' '}
                {v.measured_value != null && v.limit_value != null ? (
                  <span className="font-mono tabular">
                    {measure(v.measured_value)} / {measure(v.limit_value)} limit
                  </span>
                ) : (
                  v.code.replace(/_/g, ' ').toLowerCase()
                )}
              </li>
            ))}
          </ul>
        </div>
      )}

      <div>
        <p className="text-[11px] uppercase tracking-wide text-textMuted m-0 mb-0.5">
          Conductor upgrades ({attempts.length})
        </p>
        {attempts.length === 0 ? (
          // Not an empty table. Zero attempts is ambiguous on its own — the catalogue running out
          // and a violation no conductor choice can fix produce the identical empty list — so the
          // engine's own reason is what makes it a finding rather than a gap.
          <p className="text-[11px] text-textFaint m-0">
            {details.no_upgrade_reason || 'None attempted.'}
          </p>
        ) : (
          <ul className="m-0 list-none p-0">
            {attempts.map((a, i) => (
              <li key={i} className="text-[11px] text-text">
                <span className="font-mono text-textMuted">{a.segment_id ?? '—'}</span>{' '}
                {a.from_cable_type_id} → {a.to_cable_type_id}
                {a.pre_repair_loading_pct != null && a.post_repair_loading_pct != null && (
                  <span className="font-mono tabular text-textFaint">
                    {' '}
                    ({measure(a.pre_repair_loading_pct)}% → {measure(a.post_repair_loading_pct)}%)
                  </span>
                )}
              </li>
            ))}
          </ul>
        )}
      </div>

      {largest?.cable_type_id && (
        <p className="text-[11px] text-textFaint m-0">
          Largest of {details.catalogue_size ?? '?'} conductors:{' '}
          <span className="font-mono text-textMuted">{largest.cable_type_id}</span>
          {largest.effective_ampacity_a != null && (
            <span className="font-mono tabular"> at {measure(largest.effective_ampacity_a)} A</span>
          )}
          {largest.parallel_count != null && largest.parallel_count > 1 && ` (${largest.parallel_count}×)`}
        </p>
      )}
    </div>
  );
}

/**
 * The breached limits behind the network's violation count.
 *
 * <p>"1 violation" tells an operator something is wrong and gives them nowhere to look. Naming the
 * feeder or segment, with the measured value against the limit, is the difference between knowing
 * there is a problem and being able to act on it.
 */
function ViolationList({ violations }: { violations: ElectricalViolation[] }) {
  return (
    <div>
      <p className="text-[11.5px] uppercase tracking-wide font-bold mb-1 text-danger">
        Violations ({violations.length})
      </p>
      <ul className="m-0 list-none p-0 flex flex-col gap-1">
        {violations.map((v, i) => {
          const where = v.segment_id || v.node_id || v.feeder_id;
          const hasNumbers = v.measured_value != null && v.limit_value != null;
          return (
            <li key={`${v.code}-${i}`} className="text-[11.5px] text-text">
              <span className="font-semibold">{v.code.replace(/_/g, ' ').toLowerCase()}</span>
              {where && <span className="text-textMuted"> at {where}</span>}
              {hasNumbers && (
                <span className="font-mono tabular">
                  {' '}
                  — {measure(v.measured_value!)} vs {measure(v.limit_value!)} limit
                </span>
              )}
            </li>
          );
        })}
      </ul>
    </div>
  );
}

/**
 * Per-feeder electrical results, collapsed by default.
 *
 * <p>Python computes these for every feeder and Java only ever forwarded the network totals, so a
 * network reported as valid could still contain one feeder doing all the suffering. Collapsed
 * because on a normal run it is detail, and expanded is where an engineer goes when a total looks
 * wrong.
 */
function FeederBreakdown({ feeders }: { feeders: FeederElectricalResult[] }) {
  const [open, setOpen] = useState(false);
  const invalid = feeders.filter((f) => f.valid === false).length;

  return (
    <div>
      <button
        onClick={() => setOpen((v) => !v)}
        aria-expanded={open}
        className={`flex w-full items-center justify-between gap-2 text-[11.5px] uppercase tracking-wide font-bold mb-1 ${
          invalid > 0 ? 'text-danger' : 'text-textMuted'
        }`}
      >
        <span>
          Per-feeder electrical ({feeders.length})
          {invalid > 0 && ` — ${invalid} invalid`}
        </span>
        <span aria-hidden="true">{open ? '−' : '+'}</span>
      </button>
      {open && (
        <div className="flex flex-col gap-1">
          <div className="grid grid-cols-5 gap-x-2 text-[11px] uppercase tracking-wide text-textFaint">
            <span>Feeder</span>
            <span className="text-right">Losses</span>
            <span className="text-right">Loading</span>
            <span className="text-right">V min</span>
            <span className="text-right">V max</span>
          </div>
          {feeders.map((f) => (
            <div
              key={f.feeder_id}
              className={`grid grid-cols-5 gap-x-2 text-[11.5px] font-mono tabular ${
                f.valid === false ? 'text-danger' : 'text-text'
              }`}
            >
              <span className="font-ui">{f.feeder_id}</span>
              <span className="text-right">
                {f.active_loss_mw != null ? `${(f.active_loss_mw * 1000).toFixed(1)} kW` : '—'}
              </span>
              <span className="text-right">
                {f.maximum_loading_percent != null ? `${f.maximum_loading_percent.toFixed(1)}%` : '—'}
              </span>
              <span className="text-right">
                {f.minimum_voltage_pu != null ? f.minimum_voltage_pu.toFixed(3) : '—'}
              </span>
              <span className="text-right">
                {f.maximum_voltage_pu != null ? f.maximum_voltage_pu.toFixed(3) : '—'}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
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
