import { Card, Button } from '../../components/ui';
import { useAuditLogs } from '../../lib/query';

/**
 * Colour by consequence rather than by category: a failure or a suspension should stand out when
 * skimming, while routine sign-ins recede.
 */
const ACTION_TONE: { match: RegExp; className: string }[] = [
  { match: /FAILED|DENIED|SUSPENDED/, className: 'text-danger' },
  { match: /CREATED|IMPORTED|COMPLETED|REINSTATED/, className: 'text-accent' },
  { match: /PASSWORD|ROLE_CHANGED|UPDATED|EXPORTED/, className: 'text-warning' }
];

function toneFor(action: string): string {
  return ACTION_TONE.find((tone) => tone.match.test(action))?.className ?? 'text-textMuted';
}

function formatTimestamp(value?: string): string {
  if (!value) return '';
  const date = new Date(value);
  const today = new Date();
  const sameDay = date.toDateString() === today.toDateString();
  return sameDay ? date.toLocaleTimeString() : date.toLocaleString();
}

export function AuditPane() {
  const { data: logs = [], isLoading, isError, refetch } = useAuditLogs();

  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <h3 className="m-0 text-[11.5px] font-bold uppercase tracking-wide text-textMuted">
          Audit Log{logs.length > 0 ? ` (${logs.length})` : ''}
        </h3>
        <Button size="sm" onClick={() => refetch()}>Refresh</Button>
      </div>
      <p className="m-0 mb-2 text-[10.5px] text-textFaint">
        Most recent 50 actions. Sign-ins, account changes, imports, optimisation runs and exports.
      </p>
      {isLoading && <div className="text-[11px] text-textFaint">Loading…</div>}
      {isError && <div className="text-[11px] text-danger">Failed to load audit logs.</div>}
      {!isLoading && !isError && logs.length === 0 && (
        <div className="text-[11px] text-textFaint">No audit logs recorded yet.</div>
      )}
      <div className="flex flex-col gap-2">
        {logs.map((log, i) => (
          <div key={i} className="border-b border-border pb-2 last:border-b-0">
            <div className="flex items-baseline justify-between gap-2 text-[11px]">
              <span className="text-text font-semibold truncate">{log.username || 'anonymous'}</span>
              <span className={`font-mono text-[10px] flex-none ${toneFor(log.action || '')}`}>
                {log.action}
              </span>
            </div>
            <div className="text-[11px] text-textFaint">{log.details || log.resourceType}</div>
            <div className="text-[10px] text-textFaint mt-0.5">{formatTimestamp(log.timestamp)}</div>
          </div>
        ))}
      </div>
    </Card>
  );
}
