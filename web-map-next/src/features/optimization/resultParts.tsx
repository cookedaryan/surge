import { useState } from 'react';
import type {
  CandidateSummary,
  ElectricalViolation,
  FeederElectricalResult,
  Job,
  JobDecisionSummary,
  RepairDiagnostics
} from '../../lib/api';

/**
 * The parts a finished run's decision is reported with.
 *
 * <p>Extracted from OptimizationPane, which had grown to 734 lines carrying both the run controls
 * and every component that renders the result. They are shared rather than moved: the pane still
 * renders the full breakdown inline, and the results sheet renders the same components with more
 * room, so neither presentation can drift from the other.
 */

/** Statuses after which a job will not change again. */
export const TERMINAL_STATUSES = ['COMPLETED', 'FAILED', 'CANCELLED'];

export function parseSummary(job: Job | null): JobDecisionSummary | null {
  if (!job?.resultSummaryJson) return null;
  try {
    return JSON.parse(job.resultSummaryJson) as JobDecisionSummary;
  } catch {
    return null;
  }
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
export function CandidateComparison({
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
                {c.group_scores && c.group_scores.length > 0 && c.total_benefit_score != null && c.total_benefit_score > 0 && (
                  <div className="mt-1 flex h-1.5 w-full overflow-hidden rounded-full bg-surface2 opacity-80">
                    {c.group_scores.map((gs, i) => {
                      const SCORE_COLORS = ['bg-accent', 'bg-success', 'bg-warning', 'bg-danger', 'bg-textMuted'];
                      const width = Math.max(0, (gs.weighted_score / c.total_benefit_score!) * 100);
                      return (
                        <div
                          key={gs.group}
                          className={`h-full ${SCORE_COLORS[i % SCORE_COLORS.length]}`}
                          style={{ width: `${width}%` }}
                          title={`${gs.group}: ${gs.weighted_score.toFixed(3)} (weight: ${gs.group_weight.toFixed(2)})`}
                        />
                      );
                    })}
                  </div>
                )}
                <p className="text-[11px] text-textFaint m-0 mt-1">
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
export function measure(value: number): string {
  return String(Number(value.toFixed(4)));
}

/**
 * Failures whose message is not already shown against a candidate.
 *
 * <p>Every candidate that fails electrical validation produces both an `execution_failure` and an
 * entry in `failures`, carrying the same sentence. Rendering both repeats each failure twice — and
 * with three candidates the card became the same paragraph six times over.
 */
export function unexplainedFailures(summary: JobDecisionSummary | null) {
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
export function RepairDiagnosticsPanel({ details }: { details: RepairDiagnostics }) {
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
export function ViolationList({ violations }: { violations: ElectricalViolation[] }) {
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
export function FeederBreakdown({ feeders }: { feeders: FeederElectricalResult[] }) {
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

export function SummaryRow({
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
