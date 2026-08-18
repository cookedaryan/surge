import { Sheet, SheetSection, StatTile } from '../../components/ui';
import { useJob } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import {
  CandidateComparison,
  FeederBreakdown,
  ViolationList,
  parseSummary
} from './resultParts';
import type { FeederElectricalResult } from '../../lib/api';

/**
 * A feeder's loading against its limit, as a bar that grows from zero.
 *
 * <p>The per-feeder table gives the figures; this gives the shape. A network reported as valid can
 * still have one feeder at 94% and the rest half empty, and that is visible here in a way it is not
 * in a column of numbers.
 */
function FeederLoadBar({ feeder }: { feeder: FeederElectricalResult }) {
  const pct = feeder.maximum_loading_percent;
  if (pct == null) return null;

  const width = Math.max(0, Math.min(100, pct));
  const tone = pct >= 100 ? 'bg-danger' : pct >= 85 ? 'bg-warning' : 'bg-accent';

  return (
    <div className="flex items-center gap-2">
      <span className="w-20 flex-none truncate text-sm text-textMuted">{feeder.feeder_id}</span>
      <div className="h-1.5 flex-1 overflow-hidden rounded-full bg-surface2">
        <div
          className={`h-full rounded-full transition-[width] duration-slow ease-out ${tone}`}
          style={{ width: `${width}%` }}
        />
      </div>
      <span className="w-12 flex-none text-right font-mono text-sm tabular text-text">{pct.toFixed(1)}%</span>
    </div>
  );
}

/**
 * The full breakdown of a finished run, given room to be read.
 *
 * <p>Opens over the map rather than replacing it: these figures describe a route, and checking one
 * against the other is the whole activity. The side panel keeps the same information — this is the
 * same components with space, not a second source of truth.
 */
export function ResultsSheet() {
  const open = useUiStore((s) => s.resultsSheetOpen);
  const setOpen = useUiStore((s) => s.setResultsSheetOpen);
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const resultJobId = useUiStore((s) => s.resultJobId);

  const { data: job } = useJob(currentProjectId, resultJobId);
  const summary = parseSummary(job ?? null);

  const ns = summary?.networkSummary;
  const es = summary?.electricalSummary;
  const ps = summary?.poleSummary;
  const sc = summary?.spatialConstraintSummary;

  return (
    <Sheet
      open={open}
      onOpenChange={setOpen}
      title="Run breakdown"
      subtitle={job?.scenario ? `Optimised for ${job.scenario}` : undefined}
    >
      {!summary ? (
        <p className="text-sm text-textFaint">
          No decision summary was recorded for this run.
        </p>
      ) : (
        <>
          {summary.recommendation?.reason_details && summary.recommendation.reason_details.length > 0 && (
            <SheetSection title="Why this route" index={0}>
              <div className="flex flex-col gap-2">
                {summary.recommendation.reason_details.map((rd, i) => (
                  <div key={i} className="flex flex-col border-l-2 border-accent/40 pl-2.5">
                    <span className="text-sm font-medium text-text">{rd.message}</span>
                    {rd.metric && rd.candidate_value != null && rd.comparison_value != null && (
                      <span className="text-xs text-textFaint">
                        {rd.metric}: {rd.candidate_value.toFixed(2)} (baseline: {rd.comparison_value.toFixed(2)})
                      </span>
                    )}
                  </div>
                ))}
              </div>
            </SheetSection>
          )}

          {ns && (
            <SheetSection title="Network" index={1}>
              <div className="grid grid-cols-4 gap-2">
                <StatTile label="Feeders" value={ns.feeder_count} />
                <StatTile label="WTGs" value={ns.wtg_count} />
                <StatTile label="Segments" value={ns.segment_count} />
                <StatTile label="Length" value={ns.total_route_length_m / 1000} decimals={2} suffix=" km" />
              </div>
            </SheetSection>
          )}

          {es && (
            <SheetSection title="Electrical" index={2}>
              <div className="grid grid-cols-4 gap-2">
                <StatTile label="Converged" value={es.converged ? 'yes' : 'no'} tone={es.converged ? 'success' : 'danger'} />
                <StatTile label="Valid" value={es.valid ? 'yes' : 'no'} tone={es.valid ? 'success' : 'danger'} />
                <StatTile
                  label="Max loading"
                  value={es.maximum_loading_percent}
                  decimals={1}
                  suffix="%"
                  tone={es.maximum_loading_percent != null && es.maximum_loading_percent >= 85 ? 'warn' : 'default'}
                />
                <StatTile
                  label="Active losses"
                  value={es.total_active_loss_mw != null ? es.total_active_loss_mw * 1000 : null}
                  decimals={1}
                  suffix=" kW"
                />
              </div>
              {es.minimum_voltage_pu != null && es.maximum_voltage_pu != null && (
                <p className="mt-2 mb-0 text-sm text-textFaint">
                  Voltage range{' '}
                  <span className="font-mono tabular text-text">
                    {es.minimum_voltage_pu.toFixed(3)}–{es.maximum_voltage_pu.toFixed(3)} pu
                  </span>
                </p>
              )}
            </SheetSection>
          )}

          {summary.feeders && summary.feeders.length > 0 && (
            <SheetSection title="Feeder loading" index={3}>
              <div className="flex flex-col gap-1.5">
                {summary.feeders.map((f) => (
                  <FeederLoadBar key={f.feeder_id} feeder={f} />
                ))}
              </div>
              <div className="mt-3">
                <FeederBreakdown feeders={summary.feeders} />
              </div>
            </SheetSection>
          )}

          {ps && (
            <SheetSection title="Poles" index={4}>
              <div className="grid grid-cols-5 gap-2">
                <StatTile label="Total" value={ps.total_poles} />
                <StatTile label="Terminal" value={ps.terminal_poles} />
                <StatTile label="Angle" value={ps.angle_poles} />
                <StatTile label="Intermediate" value={ps.intermediate_poles} />
                <StatTile label="Junction" value={ps.junction_poles} />
              </div>
            </SheetSection>
          )}

          {sc && (
            <SheetSection title="Land & constraints" index={5}>
              <div className="grid grid-cols-4 gap-2">
                <StatTile
                  label="Hard violations"
                  value={sc.hard_exclusion_violation_count}
                  tone={sc.hard_exclusion_violation_count > 0 ? 'danger' : 'success'}
                />
                <StatTile label="Road crossings" value={sc.road_crossing_count} />
                <StatTile label="Affected parcels" value={sc.affected_parcel_count} />
                <StatTile label="Soft overlap" value={sc.soft_constraint_overlap_length_m} suffix=" m" />
              </div>
            </SheetSection>
          )}

          {summary.violations && summary.violations.length > 0 && (
            <SheetSection index={6}>
              <ViolationList violations={summary.violations} />
            </SheetSection>
          )}

          {summary.candidates && summary.candidates.length > 1 && (
            <SheetSection index={7}>
              <CandidateComparison
                candidates={summary.candidates}
                recommendedId={summary.recommendation?.recommended_scenario_id}
              />
            </SheetSection>
          )}
        </>
      )}
    </Sheet>
  );
}
