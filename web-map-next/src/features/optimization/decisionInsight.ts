import type { CandidateGroupScore, CandidateSummary } from '../../lib/api';

/**
 * Turning the engine's scores into the reason it chose what it chose.
 *
 * <p>Every candidate carries per-group benefit scores and the weight each group was given. The
 * ranking is the weighted sum of those, so the same numbers that decided the run can also explain
 * it — which of the operator's priorities actually moved the outcome, and where the winner is not
 * the best network on offer.
 *
 * <p>Direction is only ever claimed within a group. A higher `group_score` is better by
 * construction: they are benefit scores on a common scale, which is what makes summing them
 * meaningful. Nothing here asserts a direction for a raw engineering metric — whether more poles
 * or a longer route is "worse" is per-metric knowledge this module does not have, and the
 * candidate table deliberately shows those as absolute values for the same reason.
 */

export interface ScoreContribution {
  group: string;
  /** The candidate's benefit score for this group, before weighting. */
  score: number;
  weight: number;
  /** score x weight — what this group actually added to the total. */
  weighted: number;
  /** Share of the winner's total score, 0–100. Zero when the total is not positive. */
  sharePct: number;
}

export interface Tradeoff {
  group: string;
  /** The winner's score in this group. */
  score: number;
  /** The best score any candidate achieved in this group. */
  bestScore: number;
  /** Which candidate achieved it. */
  bestBy: string;
  /** How much benefit the winner is giving up here, in group-score units. */
  shortfall: number;
  weight: number;
}

function humanise(group: string): string {
  return group.replace(/_/g, ' ').toLowerCase();
}

/** Presentation-friendly group label: "LAND_IMPACT" reads as "land impact". */
export function groupLabel(group: string): string {
  return humanise(group);
}

/**
 * What the winner's total score is made of, largest contribution first.
 *
 * <p>Groups that contributed nothing are kept rather than dropped: a priority that was weighted and
 * still added nothing is information, and silently omitting it would make the list look like the
 * only things considered.
 */
export function scoreContributions(candidate: CandidateSummary | undefined | null): ScoreContribution[] {
  const groups = candidate?.group_scores;
  if (!groups || groups.length === 0) return [];

  const total = groups.reduce((sum, g) => sum + (g.weighted_score ?? 0), 0);

  return groups
    .map((g: CandidateGroupScore) => ({
      group: g.group,
      score: g.group_score ?? 0,
      weight: g.group_weight ?? 0,
      weighted: g.weighted_score ?? 0,
      sharePct: total > 0 ? ((g.weighted_score ?? 0) / total) * 100 : 0
    }))
    .sort((a, b) => b.weighted - a.weighted);
}

/**
 * Where the chosen network is beaten by one that was not chosen.
 *
 * <p>This is the "what it traded away" half of the explanation. A recommendation wins on the
 * weighted total, which routinely means conceding a group outright — and an engineer signing off a
 * route deserves to see that stated rather than inferred from a table of scores.
 *
 * <p>Only eligible candidates are considered. A network disqualified for, say, crossing a hard
 * exclusion is not an alternative that was given up; it is one that was never available.
 */
export function tradeoffs(
  candidates: CandidateSummary[] | undefined | null,
  recommendedId: string | null | undefined
): Tradeoff[] {
  if (!candidates || !recommendedId) return [];

  const winner = candidates.find((c) => c.scenario_id === recommendedId);
  if (!winner?.group_scores) return [];

  const rivals = candidates.filter((c) => c.scenario_id !== recommendedId && c.eligible !== false);
  if (rivals.length === 0) return [];

  const result: Tradeoff[] = [];

  for (const wg of winner.group_scores) {
    let bestScore = wg.group_score ?? 0;
    let bestBy: string | null = null;

    for (const rival of rivals) {
      const rg = rival.group_scores?.find((g) => g.group === wg.group);
      if (rg && (rg.group_score ?? 0) > bestScore) {
        bestScore = rg.group_score ?? 0;
        bestBy = rival.scenario_id;
      }
    }

    if (bestBy) {
      result.push({
        group: wg.group,
        score: wg.group_score ?? 0,
        bestScore,
        bestBy,
        shortfall: bestScore - (wg.group_score ?? 0),
        weight: wg.group_weight ?? 0
      });
    }
  }

  // Biggest concession first — that is the one worth defending in a review.
  return result.sort((a, b) => b.shortfall - a.shortfall);
}

/** The candidate that ranked immediately behind the recommendation, if there is one. */
export function runnerUp(
  candidates: CandidateSummary[] | undefined | null,
  recommendedId: string | null | undefined
): CandidateSummary | null {
  if (!candidates || candidates.length < 2) return null;
  const eligible = candidates
    .filter((c) => c.scenario_id !== recommendedId && c.eligible !== false)
    .sort((a, b) => (a.rank ?? 99) - (b.rank ?? 99));
  return eligible[0] ?? null;
}
