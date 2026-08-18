import { describe, it, expect } from 'vitest';
import { getBomCsvUrl } from './reports';

const PROJECT = '11111111-1111-1111-1111-111111111111';
const JOB = '22222222-2222-2222-2222-222222222222';

/**
 * ReportController maps these under `/projects/{projectId}/reports`, with the job segment *inside*
 * that: `@GetMapping("/jobs/{jobId}/bom/csv")`. Built the other way round the URL addressed a route
 * no controller serves, so every export after a run answered 500 — and a run is precisely when a
 * job id is in hand.
 */
describe('getBomCsvUrl', () => {
  it('nests the job under reports, where the controller maps it', () => {
    expect(getBomCsvUrl(PROJECT, JOB)).toBe(`/api/v1/projects/${PROJECT}/reports/jobs/${JOB}/bom/csv`);
  });

  it('does not put the job segment ahead of reports', () => {
    expect(getBomCsvUrl(PROJECT, JOB)).not.toContain(`/projects/${PROJECT}/jobs/`);
  });

  it('falls back to the project-latest export with no job', () => {
    expect(getBomCsvUrl(PROJECT, null)).toBe(`/api/v1/projects/${PROJECT}/reports/bom/csv`);
    expect(getBomCsvUrl(PROJECT)).toBe(`/api/v1/projects/${PROJECT}/reports/bom/csv`);
  });
});
