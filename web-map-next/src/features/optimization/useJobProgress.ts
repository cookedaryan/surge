import { useEffect, useRef, useState } from 'react';
import { api } from '../../lib/api';
import type { Job, JobProgress } from '../../lib/api';

const TERMINAL = ['COMPLETED', 'FAILED', 'CANCELLED'];

/** How often to ask the server directly, in case the stream drops or never delivers a terminal event. */
const POLL_INTERVAL_MS = 4000;

/**
 * Follows a queued optimisation to completion.
 *
 * <p>The server now returns 202 as soon as the job is queued, so the run's outcome arrives after
 * the request that started it. Progress comes from the event stream, but the stream is not trusted
 * as the only signal: a dropped connection or a proxy timeout would otherwise leave the UI showing
 * a job that runs forever. A poll runs alongside it and settles the outcome either way.
 *
 * `onSettled` receives the finished job so the caller can show the real result rather than assuming
 * success.
 */
export function useJobProgress(
  projectId: string | null,
  jobId: string | null,
  onSettled: (job: Job) => void
) {
  const [progress, setProgress] = useState<JobProgress | null>(null);
  // Kept in a ref so re-renders don't restart the subscription and re-run the effect's cleanup.
  const settledRef = useRef(false);
  const onSettledRef = useRef(onSettled);
  onSettledRef.current = onSettled;

  useEffect(() => {
    if (!projectId || !jobId) {
      setProgress(null);
      return;
    }

    settledRef.current = false;
    setProgress({ status: 'PENDING', progressPercent: 5, message: 'Queued — waiting for a worker…' });

    const settle = (job: Job) => {
      if (settledRef.current) return;
      settledRef.current = true;
      setProgress({
        status: job.status ?? 'COMPLETED',
        progressPercent: 100,
        message:
          job.status === 'FAILED'
            ? job.errorMessage || 'Optimization failed.'
            : 'Optimization completed.'
      });
      onSettledRef.current(job);
    };

    const stopStream = api.listenJobProgress(
      projectId,
      jobId,
      (data) => {
        if (!settledRef.current) setProgress(data);
      },
      () => {
        // Stream errors are not fatal on their own — the poll below establishes the real outcome.
      },
      () => {
        void api.getJobStatus(projectId, jobId).then(settle).catch(() => {});
      }
    );

    const timer = setInterval(() => {
      if (settledRef.current) return;
      void api
        .getJobStatus(projectId, jobId)
        .then((job) => {
          if (job.status && TERMINAL.includes(job.status)) settle(job);
        })
        .catch(() => {});
    }, POLL_INTERVAL_MS);

    return () => {
      stopStream();
      clearInterval(timer);
    };
  }, [projectId, jobId]);

  return progress;
}
