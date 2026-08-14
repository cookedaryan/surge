export function Legend() {
  const items: { color: string; label: string; shape?: 'dash' }[] = [
    { color: 'var(--accent)', label: 'Wind turbine' },
    { color: 'var(--warning)', label: 'Substation' },
    { color: 'var(--danger)', label: 'Restricted zone' },
    { color: 'var(--accent)', label: 'Feeder route', shape: 'dash' },
    { color: '#F59E0B', label: 'Terminal pole' },
    { color: '#EF4444', label: 'Angle pole' },
    { color: '#94A3B8', label: 'Tangent pole' },
    { color: '#8B5CF6', label: 'Junction pole' }
  ];
  return (
    <div className="absolute right-3.5 top-3.5 z-[1010] w-[172px] bg-surface border border-border rounded-lg p-2.5 font-ui pointer-events-none">
      <h4 className="m-0 mb-2 text-[10.5px] uppercase tracking-wide text-textFaint font-bold">Legend</h4>
      {items.map((item) => (
        <div key={item.label} className="flex items-center gap-1.5 py-0.5 text-[11px] text-textMuted">
          {item.shape === 'dash' ? (
            <span className="w-2.5 h-2.5 rounded-full border-2 border-dashed flex-none" style={{ borderColor: item.color }} />
          ) : (
            <span className="w-2.5 h-2.5 rounded-sm flex-none" style={{ background: item.color }} />
          )}
          {item.label}
        </div>
      ))}
    </div>
  );
}
