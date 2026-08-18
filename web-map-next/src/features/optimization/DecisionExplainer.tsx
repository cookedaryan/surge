import { StatTile } from '../../components/ui';
import { groupLabel, runnerUp, scoreContributions, tradeoffs } from './decisionInsight';
import type { CandidateSummary, JobDecisionSummary } from '../../lib/api';

/** One colour per group, matched to the stacked bar in the candidate table. */
const GROUP_COLORS = ['bg-accent', 'bg-success', 'bg-warning', 'bg-danger', 'bg-textMuted'];

/**
 * What the winning score is made of.
 *
 * <p>The engine ranks on a weighted sum of per-group benefit scores, and until now that arithmetic
 * was visible only as a 6px stacked bar with a title attribute. It is the actual answer to "why
 * this route": a group with a high score and no weight did not decide anything, and a group with a
 * modest score and most of the weight decided everything.
 */
function ScoreDecomposition({ candidate }: { candidate: CandidateSummary }) {
  const contributions = scoreContributions(candidate);
  if (contributions.length === 0) return null;

  const total = contributions.reduce((sum, c) => sum + c.weighted, 0);

  // A run can score zero across every group — a single eligible candidate has nothing to be scored
  // relative to, which is exactly when the engine reports ONLY_ELIGIBLE_CANDIDATE. Drawing four
  // empty bars and a column of 0% would dress that up as an explanation. The weights are still
  // real and still worth showing: they are the priority profile the scenario asked for.
  if (total <= 0) {
    const widestWeight = Math.max(...contributions.map((c) => c.weight), 0.0001);
    return (
      <div className="flex flex-col gap-2">
        <p className="m-0 mb-1 text-sm text-textMuted">
          No group produced a benefit score on this run, so the weighting below did not separate
          anything — the recommendation rests on eligibility rather than on scoring. These are the
          priorities the scenario applied.
        </p>
        {contributions.map((c, i) => (
          <div key={c.group}>
            <div className="flex items-baseline justify-between gap-2 mb-1">
              <span className="text-sm capitalize text-text">{groupLabel(c.group)}</span>
              <span className="font-mono text-sm tabular text-textMuted">
                {c.weight > 0 ? `weight ${c.weight.toFixed(2)}` : 'not considered'}
              </span>
            </div>
            <div className="h-2 overflow-hidden rounded-full bg-surface2">
              <div
                className={`h-full rounded-full ${c.weight > 0 ? GROUP_COLORS[i % GROUP_COLORS.length] : 'bg-transparent'}`}
                style={{ width: `${(c.weight / widestWeight) * 100}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    );
  }

  const widest = Math.max(...contributions.map((c) => Math.abs(c.weighted)), 0.0001);

  return (
    <div className="flex flex-col gap-2">
      {contributions.map((c, i) => (
        <div key={c.group}>
          <div className="flex items-baseline justify-between gap-2 mb-1">
            <span className="text-sm capitalize text-text">{groupLabel(c.group)}</span>
            <span className="font-mono text-sm tabular text-textMuted">
              {c.score.toFixed(3)} × {c.weight.toFixed(2)} ={' '}
              <span className="text-text font-semibold">{c.weighted.toFixed(3)}</span>
            </span>
          </div>
          <div className="flex items-center gap-2">
            <div className="h-2 flex-1 overflow-hidden rounded-full bg-surface2">
              <div
                className={`h-full rounded-full transition-[width] duration-slow ease-out ${GROUP_COLORS[i % GROUP_COLORS.length]}`}
                style={{ width: `${Math.max(0, (c.weighted / widest) * 100)}%` }}
              />
            </div>
            <span className="w-11 flex-none text-right font-mono text-xs tabular text-textFaint">
              {c.sharePct.toFixed(0)}%
            </span>
          </div>
        </div>
      ))}
      <p className="m-0 mt-0.5 text-xs text-textFaint">
        Bars are each group's weighted contribution; the percentage is its share of the total score.
      </p>
    </div>
  );
}

/**
 * Where the chosen network is beaten by one that was not chosen.
 *
 * <p>A recommendation wins on the weighted total, which routinely means conceding a group outright.
 * Saying so is the difference between a result an engineer can sign off and one they have to take
 * on trust — and it is the first thing they will be asked in review.
 */
function Tradeoffs({ summary }: { summary: JobDecisionSummary }) {
  const given = tradeoffs(summary.candidates, summary.recommendation?.recommended_scenario_id);

  if (given.length === 0) {
    // Distinct from having no comparison at all: leading every group is a real, and strong, result.
    if (!summary.candidates || summary.candidates.length < 2) return null;
    return (
      <p className="m-0 flex items-start gap-1.5 text-sm text-success">
        <svg viewBox="0 0 24 24" className="mt-px h-3.5 w-3.5 flex-none" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M20 6 9 17l-5-5" />
        </svg>
        Nothing given up — this route scored at least as well as every eligible alternative in every
        group.
      </p>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {given.map((t) => (
        <div key={t.group} className="rounded-md border border-warning/35 bg-warningSoft px-2.5 py-2">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm font-medium capitalize text-text">{groupLabel(t.group)}</span>
            <span className="font-mono text-sm tabular text-warning">−{t.shortfall.toFixed(3)}</span>
          </div>
          <p className="m-0 mt-0.5 text-xs leading-relaxed text-textMuted">
            Scored <span className="font-mono tabular text-text">{t.score.toFixed(3)}</span> where{' '}
            <span className="font-mono text-text">{t.bestBy}</span> reached{' '}
            <span className="font-mono tabular text-text">{t.bestScore.toFixed(3)}</span>. That group
            carried {(t.weight * 100).toFixed(0)}% weight, so the loss here was outweighed elsewhere.
          </p>
        </div>
      ))}
    </div>
  );
}

/** The winner beside the candidate that ranked immediately behind it. */
function HeadToHead({ summary }: { summary: JobDecisionSummary }) {
  const recommendedId = summary.recommendation?.recommended_scenario_id;
  const winner = summary.candidates?.find((c) => c.scenario_id === recommendedId);
  const rival = runnerUp(summary.candidates, recommendedId);
  if (!winner || !rival) return null;

  const rows: [string, (m: NonNullable<CandidateSummary['engineering_metrics']>) => string][] = [
    ['Route length', (m) => (m.total_route_length_m != null ? `${(m.total_route_length_m / 1000).toFixed(2)} km` : '—')],
    ['Poles', (m) => (m.physical_pole_count != null ? String(m.physical_pole_count) : '—')],
    ['Active losses', (m) => (m.total_active_loss_mw != null ? `${(m.total_active_loss_mw * 1000).toFixed(0)} kW` : '—')],
    ['Max loading', (m) => (m.maximum_loading_percent != null ? `${m.maximum_loading_percent.toFixed(1)}%` : '—')],
    ['Road crossings', (m) => (m.road_crossing_count != null ? String(m.road_crossing_count) : '—')],
    ['Affected parcels', (m) => (m.affected_parcel_count != null ? String(m.affected_parcel_count) : '—')],
    ['Environmental overlap', (m) => (m.environmental_overlap_m2 != null ? `${m.environmental_overlap_m2.toFixed(0)} m²` : '—')]
  ];

  const wm = winner.engineering_metrics;
  const rm = rival.engineering_metrics;
  if (!wm || !rm) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-left text-sm">
        <thead>
          <tr className="text-xs uppercase tracking-wide text-textFaint">
            <th className="pb-1.5 font-medium">Metric</th>
            <th className="pb-1.5 pl-2 text-right font-medium text-accent">{winner.scenario_id} ★</th>
            <th className="pb-1.5 pl-2 text-right font-medium">{rival.scenario_id}</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-border">
          {rows.map(([label, read]) => (
            <tr key={label}>
              <td className="py-1 text-textMuted">{label}</td>
              <td className="py-1 pl-2 text-right font-mono tabular font-semibold text-accent">{read(wm)}</td>
              <td className="py-1 pl-2 text-right font-mono tabular text-text">{read(rm)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {/* Absolute values, deliberately. Whether a longer route or an extra pole is worse is
          per-metric knowledge this table does not have, and printing a delta would assert it. */}
      <p className="m-0 mt-2 text-xs text-textFaint">
        Measured values, not improvements — which direction counts as better differs per metric and
        is already expressed by the weighted score above.
      </p>
    </div>
  );
}

export function DecisionExplainer({ summary }: { summary: JobDecisionSummary }) {
  const recommendedId = summary.recommendation?.recommended_scenario_id;
  const winner = summary.candidates?.find((c) => c.scenario_id === recommendedId);
  const reasons = summary.recommendation?.reason_details;
  const evaluated = summary.candidates?.length ?? 0;
  const ruledOut = summary.candidates?.filter((c) => c.eligible === false).length ?? 0;
  const hasRivals = (summary.candidates?.filter((c) => c.eligible !== false).length ?? 0) > 1;
  const hasRunnerUp = !!runnerUp(summary.candidates, recommendedId)?.engineering_metrics && !!winner?.engineering_metrics;

  return (
    <div className="flex flex-col gap-5">
      <div className="grid grid-cols-3 gap-2">
        <StatTile label="Alternatives evaluated" value={evaluated} />
        <StatTile
          label="Ruled out"
          value={ruledOut}
          tone={ruledOut > 0 ? 'warn' : 'default'}
          hint={ruledOut > 0 ? 'ineligible' : undefined}
        />
        <StatTile
          label="Benefit score"
          value={winner?.total_benefit_score ?? null}
          decimals={3}
          tone="success"
        />
      </div>

      {reasons && reasons.length > 0 && (
        <section>
          <h4 className="m-0 mb-2 text-sm font-bold uppercase tracking-wide text-textMuted">
            What the engine reported
          </h4>
          <div className="flex flex-col gap-2">
            {reasons.map((rd, i) => (
              <div key={i} className="flex flex-col border-l-2 border-accent/40 pl-2.5">
                <span className="text-sm font-medium text-text">{rd.message}</span>
                {rd.metric && rd.candidate_value != null && rd.comparison_value != null && (
                  <span className="font-mono text-xs tabular text-textFaint">
                    {rd.metric}: {rd.candidate_value.toFixed(2)} (baseline {rd.comparison_value.toFixed(2)})
                  </span>
                )}
              </div>
            ))}
          </div>
        </section>
      )}

      {winner && (
        <section>
          <h4 className="m-0 mb-2 text-sm font-bold uppercase tracking-wide text-textMuted">
            What the score is made of
          </h4>
          <ScoreDecomposition candidate={winner} />
        </section>
      )}

      {/* Both of these compare against alternatives, so both are absent on a run that produced only
          one eligible candidate. Rendered unconditionally they left their headings standing over
          nothing, which reads as data that failed to load rather than a comparison that does not
          exist. */}
      {hasRivals && (
        <section>
          <h4 className="m-0 mb-2 text-sm font-bold uppercase tracking-wide text-textMuted">
            What it gave up
          </h4>
          <Tradeoffs summary={summary} />
        </section>
      )}

      {hasRunnerUp && (
        <section>
          <h4 className="m-0 mb-2 text-sm font-bold uppercase tracking-wide text-textMuted">
            Against the runner-up
          </h4>
          <HeadToHead summary={summary} />
        </section>
      )}

      {!hasRivals && (
        <p className="m-0 rounded-md border border-border bg-surface2 px-2.5 py-2 text-sm text-textMuted">
          Only one candidate survived eligibility on this run, so there is nothing to compare it
          against. A scenario that produces several alternatives will show what was traded away and
          how the runner-up measured up.
        </p>
      )}
    </div>
  );
}
