import { useEffect, useState } from 'react';
import { api } from '../../lib/api';
import type { JobProgress } from '../../lib/api';

export function useJobProgress(projectId: string | null, jobId: string | null, onComplete: () => void) {
  const [progress, setProgress] = useState<JobProgress | null>(null);

  useEffect(() => {
    if (!projectId || !jobId) {
      setProgress(null);
      return;
    }
    setProgress({ status: 'RUNNING', progressPercent: 10, message: 'Initializing optimization job request...' });
    const stop = api.listenJobProgress(
      projectId,
      jobId,
      (data) => setProgress(data),
      (err) => setProgress({ status: 'FAILED', message: err.message }),
      () => {
        setProgress({ status: 'COMPLETED', progressPercent: 100, message: 'Optimization completed cleanly!' });
        onComplete();
      }
    );
    return stop;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId, jobId]);

  return progress;
}
