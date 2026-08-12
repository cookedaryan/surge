import { Card, Button } from '../../components/ui';
import { useAuditLogs } from '../../lib/query';

export function AuditPane() {
  const { data: logs = [], isLoading, isError, refetch } = useAuditLogs();

  return (
    <Card>
      <div className="flex items-center justify-between mb-2">
        <h3 className="m-0 text-[11.5px] font-bold uppercase tracking-wide text-textMuted">Audit Log</h3>
        <Button size="sm" onClick={() => refetch()}>Refresh</Button>
      </div>
      {isLoading && <div className="text-[11px] text-textFaint">Loading…</div>}
      {isError && <div className="text-[11px] text-danger">Failed to load audit logs.</div>}
      {!isLoading && !isError && logs.length === 0 && (
        <div className="text-[11px] text-textFaint">No audit logs recorded yet.</div>
      )}
      <div className="flex flex-col gap-2">
        {logs.map((log, i) => (
          <div key={i} className="border-b border-border pb-2 last:border-b-0">
            <div className="flex items-center justify-between text-[11px]">
              <span className="text-text font-semibold">{log.username || 'anonymous'}</span>
              <span className="text-textMuted">{log.action}</span>
            </div>
            <div className="text-[11px] text-textFaint">{log.details || log.resourceType}</div>
            <div className="text-[10px] text-textFaint mt-0.5">
              {log.timestamp ? new Date(log.timestamp).toLocaleTimeString() : ''}
            </div>
          </div>
        ))}
      </div>
    </Card>
  );
}
