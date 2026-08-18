import { useEffect, useState } from 'react';
import { useJob } from '../lib/query';
import { useUiStore } from '../lib/store';

const TERMINAL_STATUSES = ['COMPLETED', 'FAILED', 'CANCELLED'];

function formatElapsed(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m > 0 ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`;
}

/**
 * Shows a run in flight from anywhere in the app, and opens its results when it lands.
 *
 * <p>The optimisation pane is one of six tabs, so an operator who starts a run and moves on had no
 * indication it was still going. The chip is the ambient answer: it says a run is happening, how
 * long it has been happening, and — once finished — offers the result rather than waiting to be
 * found.
 *
 * <p>The elapsed timer is measured from when this component first saw the job running, not from
 * the job's queue time, and is presented as elapsed rather than remaining. The server reports
 * progress but not an estimate, and inventing a countdown from a percentage that moves in jumps
 * would be inventing information.
 */
export function RunStatusChip() {
  const currentProjectId = useUiStore((s) => s.currentProjectId);
  const currentJobId = useUiStore((s) => s.currentJobId);
  const resultJobId = useUiStore((s) => s.resultJobId);
  const setResultsSheetOpen = useUiStore((s) => s.setResultsSheetOpen);

  const { data: job } = useJob(currentProjectId, currentJobId);
  const running = !!currentJobId && !!job && !TERMINAL_STATUSES.includes(job.status ?? '');

  const [startedAt, setStartedAt] = useState<number | null>(null);
  const [now, setNow] = useState(() => Date.now());

  useEffect(() => {
    if (!running) {
      setStartedAt(null);
      return;
    }
    setStartedAt((prev) => prev ?? Date.now());
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);

  if (running) {
    return (
      <div className="flex items-center gap-2 rounded-md border border-accent/40 bg-accent100 px-2.5 h-7 text-sm text-text">
        <span className="relative flex h-1.5 w-1.5">
          <span className="absolute inline-flex h-full w-full rounded-full bg-accent animate-pulse-ring" />
          <span className="relative inline-flex h-1.5 w-1.5 rounded-full bg-accent" />
        </span>
        <span className="font-semibold">Optimising</span>
        {startedAt && <span className="tabular text-textMuted">{formatElapsed(now - startedAt)}</span>}
      </div>
    );
  }

  if (resultJobId) {
    return (
      <button
        onClick={() => setResultsSheetOpen(true)}
        className="flex items-center gap-1.5 rounded-md border border-border bg-surface2 px-2.5 h-7 text-sm text-textMuted
                   transition-colors duration-fast ease-out hover:text-text hover:border-borderStrong"
      >
        <span className="h-1.5 w-1.5 rounded-full bg-success" />
        Last run
      </button>
    );
  }

  return null;
}
