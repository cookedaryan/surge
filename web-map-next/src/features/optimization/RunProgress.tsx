import { useEffect, useState } from 'react';
import type { JobProgress } from '../../lib/api';

function formatElapsed(ms: number): string {
  const total = Math.floor(ms / 1000);
  const m = Math.floor(total / 60);
  const s = total % 60;
  return m > 0 ? `${m}m ${String(s).padStart(2, '0')}s` : `${s}s`;
}

/**
 * A run in flight.
 *
 * <p>Everything shown here comes from the server. The percentage is the stream's own
 * `progressPercent` and the caption is its own message — no stage is inferred from the text, and no
 * completion time is estimated. The engine reports progress in jumps, and a smooth countdown
 * derived from that would be a prediction the app is in no position to make.
 *
 * <p>The elapsed timer is the honest thing it can add: it is measured, it always moves, and it
 * tells an operator whether a run that has sat at the same percentage is still alive.
 */
export function RunProgress({ progress }: { progress: JobProgress }) {
  const [startedAt] = useState(() => Date.now());
  const [now, setNow] = useState(() => Date.now());
  const failed = progress.status === 'FAILED';

  useEffect(() => {
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, []);

  const percent = Math.max(0, Math.min(100, progress.progressPercent ?? 10));

  return (
    <div className="mt-1">
      <div
        role="progressbar"
        aria-valuenow={Math.round(percent)}
        aria-valuemin={0}
        aria-valuemax={100}
        aria-label="Optimisation progress"
        className="h-1.5 rounded-full bg-surface2 overflow-hidden"
      >
        <div
          className={`h-full rounded-full transition-[width] duration-slow ease-out ${failed ? 'bg-danger' : 'bg-accent'}`}
          style={{ width: `${percent}%` }}
        />
      </div>
      <div className="mt-1.5 flex items-baseline justify-between gap-2">
        <p className="text-sm text-textFaint m-0">{progress.message}</p>
        <span className="text-sm text-textFaint tabular flex-none">{formatElapsed(now - startedAt)}</span>
      </div>
    </div>
  );
}
