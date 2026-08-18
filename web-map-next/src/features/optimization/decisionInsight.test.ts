import { describe, it, expect } from 'vitest';
import { scoreContributions, tradeoffs, runnerUp } from './decisionInsight';
import type { CandidateSummary } from '../../lib/api';

/**
 * The arithmetic behind "why this route". These figures decide the run, so the explanation drawn
 * from them has to be the same arithmetic rather than a plausible retelling of it.
 */

function candidate(
  id: string,
  groups: [string, number, number][],
  extra: Partial<CandidateSummary> = {}
): CandidateSummary {
  return {
    scenario_id: id,
    group_scores: groups.map(([group, group_score, group_weight]) => ({
      group,
      group_score,
      group_weight,
      weighted_score: group_score * group_weight
    })),
    ...extra
  };
}

describe('scoreContributions', () => {
  it('ranks groups by what they actually added, not by their raw score', () => {
    // Environment scores higher but is barely weighted; cost is what moved the total.
    const c = candidate('A', [
      ['COST', 0.6, 0.8],
      ['ENVIRONMENT', 0.9, 0.1]
    ]);

    const [first, second] = scoreContributions(c);

    expect(first.group).toBe('COST');
    expect(first.weighted).toBeCloseTo(0.48);
    expect(second.group).toBe('ENVIRONMENT');
    expect(second.weighted).toBeCloseTo(0.09);
  });

  it('expresses each group as a share of the total', () => {
    const c = candidate('A', [
      ['COST', 0.5, 1 ],
      ['LAND', 0.5, 1 ]
    ]);

    const shares = scoreContributions(c).map((s) => Math.round(s.sharePct));

    expect(shares).toEqual([50, 50]);
  });

  it('keeps a weighted group that contributed nothing', () => {
    // A priority that was asked for and delivered none of its benefit is a finding, not noise.
    const c = candidate('A', [
      ['COST', 0.7, 1 ],
      ['ENVIRONMENT', 0, 0.5]
    ]);

    const groups = scoreContributions(c).map((s) => s.group);

    expect(groups).toContain('ENVIRONMENT');
  });

  it('does not divide by a total of zero', () => {
    const c = candidate('A', [['COST', 0, 0.5]]);

    expect(scoreContributions(c)[0].sharePct).toBe(0);
  });

  it('returns nothing when the engine reported no group scores', () => {
    expect(scoreContributions({ scenario_id: 'A' })).toEqual([]);
    expect(scoreContributions(null)).toEqual([]);
  });
});

describe('tradeoffs', () => {
  const winner = candidate('A', [
    ['COST', 0.9, 0.7],
    ['ENVIRONMENT', 0.3, 0.3]
  ], { rank: 1 });

  it('names the group given up, and who did better on it', () => {
    const rival = candidate('B', [
      ['COST', 0.4, 0.7],
      ['ENVIRONMENT', 0.8, 0.3]
    ], { rank: 2 });

    const result = tradeoffs([winner, rival], 'A');

    expect(result).toHaveLength(1);
    expect(result[0].group).toBe('ENVIRONMENT');
    expect(result[0].bestBy).toBe('B');
    expect(result[0].shortfall).toBeCloseTo(0.5);
  });

  it('reports nothing given up when the winner leads every group', () => {
    const rival = candidate('B', [
      ['COST', 0.2, 0.7],
      ['ENVIRONMENT', 0.1, 0.3]
    ], { rank: 2 });

    expect(tradeoffs([winner, rival], 'A')).toEqual([]);
  });

  it('ignores candidates that were disqualified', () => {
    // A network ruled out for crossing a hard exclusion is not an alternative that was given up;
    // it was never available to choose.
    const ineligible = candidate('B', [
      ['COST', 0.4, 0.7],
      ['ENVIRONMENT', 0.99, 0.3]
    ], { rank: 2, eligible: false });

    expect(tradeoffs([winner, ineligible], 'A')).toEqual([]);
  });

  it('puts the largest concession first', () => {
    const rival = candidate('B', [
      ['COST', 0.95, 0.7],
      ['ENVIRONMENT', 0.9, 0.3]
    ], { rank: 2 });

    const groups = tradeoffs([winner, rival], 'A').map((t) => t.group);

    expect(groups).toEqual(['ENVIRONMENT', 'COST']);
  });

  it('returns nothing without a recommendation to explain', () => {
    expect(tradeoffs([winner], null)).toEqual([]);
  });
});

describe('runnerUp', () => {
  it('picks the best-ranked eligible candidate that did not win', () => {
    const a = candidate('A', [['COST', 0.9, 1]], { rank: 1 });
    const b = candidate('B', [['COST', 0.8, 1]], { rank: 2 });
    const c = candidate('C', [['COST', 0.7, 1]], { rank: 3 });

    expect(runnerUp([a, b, c], 'A')?.scenario_id).toBe('B');
  });

  it('skips a disqualified candidate that would otherwise rank second', () => {
    const a = candidate('A', [['COST', 0.9, 1]], { rank: 1 });
    const b = candidate('B', [['COST', 0.8, 1]], { rank: 2, eligible: false });
    const c = candidate('C', [['COST', 0.7, 1]], { rank: 3 });

    expect(runnerUp([a, b, c], 'A')?.scenario_id).toBe('C');
  });

  it('has no runner-up when only one candidate was produced', () => {
    expect(runnerUp([candidate('A', [['COST', 0.9, 1]])], 'A')).toBeNull();
  });
});
