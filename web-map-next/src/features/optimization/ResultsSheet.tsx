import { useState } from 'react';
import { Sheet, SheetSection, StatTile, Skeleton } from '../../components/ui';
import { useJob, useJobBomReport } from '../../lib/query';
import { useUiStore } from '../../lib/store';
import { formatMoney } from '../../lib/format/money';
import { CandidateComparison, FeederBreakdown, ViolationList, parseSummary } from './resultParts';
import { DecisionExplainer } from './DecisionExplainer';
import { CostBreakdown } from '../bom/CostBreakdown';
import { BomBoqTable } from '../bom/BomBoqTable';
import type { FeederElectricalResult } from '../../lib/api';

type Tab = 'decision' | 'network' | 'cost';

const TABS: { id: Tab; label: string }[] = [
  { id: 'decision', label: 'Decision' },
  { id: 'network', label: 'Network' },
  { id: 'cost', label: 'Cost' }
];

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
 * against the other is the whole activity.
 *
 * <p>Split three ways because the questions are different. "Why this one" is a decision an engineer
 * has to defend, "is it sound" is an engineering check, and "what does it cost" is a commercial
 * one — stacked in a single column they interleave into one long scroll where the reasoning is
 * buried among conductor schedules.
 */
export function ResultsSheet() {
  const open = useUiStore((s) => s.resultsSheetOpen);
  const setOpen = useUiStore((s) => s.setResultsSheetOpen);
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const resultJobId = useUiStore((s) => s.resultJobId);
  const [tab, setTab] = useState<Tab>('decision');

  const { data: job } = useJob(currentProjectId, resultJobId);
  const summary = parseSummary(job ?? null);

  // Scoped to this run, not the project's most recently costed one, so the money on screen belongs
  // to the decision beside it.
  const { data: bom, isLoading: bomLoading, isError: bomError } = useJobBomReport(currentProjectId, resultJobId);

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
      widthClassName="w-[760px]"
    >
      {!summary ? (
        <p className="text-sm text-textFaint">No decision summary was recorded for this run.</p>
      ) : (
        <>
          <div className="mb-4 grid grid-cols-4 gap-2">
            <StatTile
              label="Route length"
              value={ns ? ns.total_route_length_m / 1000 : null}
              decimals={2}
              suffix=" km"
            />
            <StatTile label="Poles" value={ps?.total_poles ?? null} />
            <StatTile label="Est. CapEx" value={bom ? formatMoney(bom.totalEstimatedCost, bom.costCurrency) : null} />
            <StatTile
              label="Losses"
              value={es?.total_active_loss_mw != null ? es.total_active_loss_mw * 1000 : null}
              decimals={1}
              suffix=" kW"
            />
          </div>

          <div role="tablist" aria-label="Run breakdown sections" className="mb-4 flex gap-1 border-b border-border">
            {TABS.map((t) => (
              <button
                key={t.id}
                role="tab"
                aria-selected={tab === t.id}
                onClick={() => setTab(t.id)}
                className={`relative -mb-px px-3 py-1.5 text-sm font-semibold transition-colors duration-fast ease-out ${
                  tab === t.id
                    ? 'text-accent border-b-2 border-accent'
                    : 'text-textMuted border-b-2 border-transparent hover:text-text'
                }`}
              >
                {t.label}
              </button>
            ))}
          </div>

          {tab === 'decision' && (
            <div className="animate-fade-in">
              <DecisionExplainer summary={summary} />
              {summary.candidates && summary.candidates.length > 1 && (
                <div className="mt-5">
                  <CandidateComparison
                    candidates={summary.candidates}
                    recommendedId={summary.recommendation?.recommended_scenario_id}
                  />
                </div>
              )}
            </div>
          )}

          {tab === 'network' && (
            <div className="animate-fade-in">
              {ns && (
                <SheetSection title="Network" index={0}>
                  <div className="grid grid-cols-4 gap-2">
                    <StatTile label="Feeders" value={ns.feeder_count} />
                    <StatTile label="WTGs" value={ns.wtg_count} />
                    <StatTile label="Segments" value={ns.segment_count} />
                    <StatTile label="Length" value={ns.total_route_length_m / 1000} decimals={2} suffix=" km" />
                  </div>
                </SheetSection>
              )}

              {es && (
                <SheetSection title="Electrical" index={1}>
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
                      {es.solver_algorithm ? <span className="text-textFaint"> · {es.solver_algorithm}</span> : null}
                    </p>
                  )}
                </SheetSection>
              )}

              {summary.feeders && summary.feeders.length > 0 && (
                <SheetSection title="Feeder loading" index={2}>
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
                <SheetSection title="Poles" index={3}>
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
                <SheetSection title="Land & constraints" index={4}>
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
                <SheetSection index={5}>
                  <ViolationList violations={summary.violations} />
                </SheetSection>
              )}
            </div>
          )}

          {tab === 'cost' && (
            <div className="animate-fade-in">
              {bomLoading && <Skeleton className="h-40" />}

              {bomError && (
                <p role="alert" className="text-sm text-danger">
                  The bill of materials for this run could not be loaded.
                </p>
              )}

              {bom && (
                <>
                  <SheetSection title="Bill of materials" index={0}>
                    <CostBreakdown bom={bom} />
                  </SheetSection>

                  {(bom.landCostBasis || bom.ownerInteractionCount != null || bom.landIsFeasible != null) && (
                    <SheetSection title="Land acquisition" index={1}>
                      <div className="space-y-1.5 rounded-md border border-border bg-surface2 p-3 text-sm">
                        {bom.landIsFeasible != null && (
                          <div className="flex justify-between gap-3">
                            <span className="text-textFaint">Acquisition feasible</span>
                            <span className={bom.landIsFeasible ? 'text-success' : 'text-danger'}>
                              {bom.landIsFeasible ? 'yes' : 'no'}
                            </span>
                          </div>
                        )}
                        {bom.ownerInteractionCount != null && (
                          <div className="flex justify-between gap-3">
                            <span className="text-textFaint">Owners to negotiate with</span>
                            <span className="font-mono tabular text-text">{bom.ownerInteractionCount}</span>
                          </div>
                        )}
                        {bom.ownerInteractionBasis && (
                          <div className="flex justify-between gap-3">
                            <span className="text-textFaint">Basis</span>
                            <span className="text-text">{bom.ownerInteractionBasis}</span>
                          </div>
                        )}
                        {bom.landCostBasis && (
                          <div className="flex justify-between gap-3">
                            <span className="text-textFaint">Land cost basis</span>
                            <span className="text-text">{bom.landCostBasis}</span>
                          </div>
                        )}
                        <div className="flex justify-between gap-3 border-t border-border pt-1.5 mt-1.5">
                          <span className="text-textFaint">Compensation</span>
                          <span className="font-mono tabular text-text">
                            {formatMoney(bom.totalCompensationCost, bom.costCurrency)}
                          </span>
                        </div>
                      </div>
                    </SheetSection>
                  )}

                  <SheetSection title="Bill of quantities" index={2}>
                    <BomBoqTable bom={bom} bare />
                  </SheetSection>
                </>
              )}
            </div>
          )}
        </>
      )}
    </Sheet>
  );
}
