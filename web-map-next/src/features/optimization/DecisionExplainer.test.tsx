import { describe, it, expect } from 'vitest';
import { render, screen, within } from '@testing-library/react';
import { DecisionExplainer } from './DecisionExplainer';
import type { CandidateSummary, JobDecisionSummary } from '../../lib/api';

/**
 * The comparison sections only exist on a run that produced rivals.
 *
 * <p>Real sites kept collapsing to a single candidate — the generator suppresses duplicate
 * topologies, and a small regular layout yields the same network from every parameter personality —
 * so these fixtures stand in for the multi-candidate runs that reach production.
 */

function candidate(
  id: string,
  groups: [string, number, number][],
  metrics: Partial<NonNullable<CandidateSummary['engineering_metrics']>> = {},
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
    engineering_metrics: {
      total_route_length_m: 70_000,
      physical_pole_count: 1145,
      total_active_loss_mw: 2.637,
      maximum_loading_percent: 88.4,
      road_crossing_count: 3,
      affected_parcel_count: 12,
      environmental_overlap_m2: 0,
      ...metrics
    },
    ...extra
  };
}

/** A winner that leads on cost but concedes environment to SCN-002. */
function multiCandidateSummary(): JobDecisionSummary {
  return {
    recommendation: {
      recommended_scenario_id: 'SCN-001',
      reason_details: [
        {
          code: 'LOWEST_TRAVERSAL_COST',
          message: 'Shortest routed length of the eligible candidates',
          metric: 'total_route_length_m',
          candidate_value: 70_000,
          comparison_value: 135_800
        }
      ]
    },
    candidates: [
      candidate('SCN-001', [['COST', 0.9, 0.7], ['ENVIRONMENT', 0.3, 0.3]], {}, {
        rank: 1,
        total_benefit_score: 0.72,
        eligible: true
      }),
      candidate('SCN-002', [['COST', 0.4, 0.7], ['ENVIRONMENT', 0.8, 0.3]], {
        total_route_length_m: 135_800,
        physical_pole_count: 1980,
        environmental_overlap_m2: 4200
      }, { rank: 2, total_benefit_score: 0.52, eligible: true }),
      candidate('SCN-003', [['COST', 0.5, 0.7], ['ENVIRONMENT', 0.5, 0.3]], {}, {
        rank: 3,
        total_benefit_score: 0.5,
        eligible: false,
        disqualifications: ['Exceeded voltage limit']
      })
    ]
  };
}

describe('DecisionExplainer with several candidates', () => {
  it('decomposes the winning score instead of falling back to the weight profile', () => {
    render(<DecisionExplainer summary={multiCandidateSummary()} />);

    // The real decomposition prints score x weight = contribution; the zero-score fallback does not.
    expect(screen.getByText(/0\.900/)).toBeTruthy();
    expect(screen.getByText(/0\.630/)).toBeTruthy();
    expect(screen.queryByText(/No group produced a benefit score/i)).toBeNull();
  });

  it('shows each group as a share of the total score', () => {
    render(<DecisionExplainer summary={multiCandidateSummary()} />);

    // cost 0.63 and environment 0.09 of 0.72 => 88% / 13% (rounded).
    expect(screen.getByText('88%')).toBeTruthy();
    expect(screen.getByText('13%')).toBeTruthy();
  });

  it('names what was given up, to whom, and by how much', () => {
    render(<DecisionExplainer summary={multiCandidateSummary()} />);

    const heading = screen.getByText(/what it gave up/i);
    const section = heading.closest('section') as HTMLElement;

    expect(within(section).getByText(/environment/i)).toBeTruthy();
    expect(within(section).getByText('SCN-002')).toBeTruthy();
    expect(within(section).getByText(/−0\.500/)).toBeTruthy();
    // The concession is only defensible alongside the weight it was traded against.
    expect(within(section).getByText(/30% weight/)).toBeTruthy();
  });

  it('does not count a disqualified candidate as something given up', () => {
    const summary = multiCandidateSummary();
    // SCN-003 is ineligible and must not appear as a rival that beat the winner anywhere.
    const section = (render(<DecisionExplainer summary={summary} />),
      screen.getByText(/what it gave up/i).closest('section') as HTMLElement);

    expect(within(section).queryByText('SCN-003')).toBeNull();
  });

  it('puts the winner beside the runner-up on measured values', () => {
    render(<DecisionExplainer summary={multiCandidateSummary()} />);

    const heading = screen.getByText(/against the runner-up/i);
    const section = heading.closest('section') as HTMLElement;

    expect(within(section).getByText(/SCN-001/)).toBeTruthy();
    expect(within(section).getByText('SCN-002')).toBeTruthy();
    // Both networks' route lengths, in km, side by side.
    expect(within(section).getByText('70.00 km')).toBeTruthy();
    expect(within(section).getByText('135.80 km')).toBeTruthy();
    expect(within(section).getByText('1980')).toBeTruthy();
  });

  it('skips the ineligible candidate when choosing the runner-up', () => {
    const summary = multiCandidateSummary();
    summary.candidates![1].eligible = false;
    render(<DecisionExplainer summary={summary} />);

    // SCN-002 is out, SCN-003 is out, so there is no runner-up left to compare against.
    expect(screen.queryByText(/against the runner-up/i)).toBeNull();
  });

  it('reports a clean sweep rather than an empty trade-off list', () => {
    const summary = multiCandidateSummary();
    // Make the winner lead every group.
    summary.candidates![1].group_scores = [
      { group: 'COST', group_score: 0.2, group_weight: 0.7, weighted_score: 0.14 },
      { group: 'ENVIRONMENT', group_score: 0.1, group_weight: 0.3, weighted_score: 0.03 }
    ];
    render(<DecisionExplainer summary={summary} />);

    expect(screen.getByText(/nothing given up/i)).toBeTruthy();
  });

  it('counts the alternatives and the ones ruled out', () => {
    render(<DecisionExplainer summary={multiCandidateSummary()} />);

    // The label is itself a div, so closest('div') returns the label; the tile is its parent.
    const tileFor = (label: RegExp) =>
      screen.getByText(label).parentElement as HTMLElement;

    expect(tileFor(/alternatives evaluated/i).textContent).toMatch(/^3/);
    expect(tileFor(/ruled out/i).textContent).toMatch(/^1/);
  });
});

describe('DecisionExplainer with a single candidate', () => {
  const soleCandidate: JobDecisionSummary = {
    recommendation: {
      recommended_scenario_id: 'SCN-001',
      reason_details: [
        { code: 'ONLY_ELIGIBLE_CANDIDATE', message: 'Only one candidate satisfied all eligibility checks' }
      ]
    },
    candidates: [
      candidate('SCN-001', [
        ['PHYSICAL', 0, 0.4],
        ['SPATIAL', 0, 0],
        ['ELECTRICAL', 0, 0.6]
      ], {}, { rank: 1, total_benefit_score: 0, eligible: true })
    ]
  };

  it('shows the weighting applied rather than a row of empty bars', () => {
    render(<DecisionExplainer summary={soleCandidate} />);

    expect(screen.getByText(/No group produced a benefit score/i)).toBeTruthy();
    expect(screen.getByText('weight 0.60')).toBeTruthy();
    // A group carrying no weight was not part of the decision, and says so.
    expect(screen.getByText('not considered')).toBeTruthy();
  });

  it('omits both comparison sections instead of leaving empty headings', () => {
    render(<DecisionExplainer summary={soleCandidate} />);

    expect(screen.queryByText(/what it gave up/i)).toBeNull();
    expect(screen.queryByText(/against the runner-up/i)).toBeNull();
    expect(screen.getByText(/nothing to compare it against/i)).toBeTruthy();
  });
});
