import { useState } from 'react';

/**
 * What the symbols on the map mean.
 *
 * <p>Every entry pairs its colour with a distinct shape or line style. The report's C-17 is about
 * feeder colours being indistinguishable under colour vision deficiency; the same reasoning applies
 * to the legend itself, so nothing here is identified by hue alone.
 */
const ENTRIES: { label: string; swatch: JSX.Element }[] = [
  {
    label: 'Turbine (WTG)',
    swatch: <span className="h-2.5 w-2.5 rounded-full border-2 border-accent bg-accent" />
  },
  {
    label: 'Substation',
    swatch: <span className="h-2.5 w-2.5 rounded-[2px] border-2 border-warning bg-warning" />
  },
  {
    label: 'Evacuation tower',
    swatch: <span className="h-2.5 w-2.5 rounded-full border-2 border-borderStrong bg-surface2" />
  },
  {
    label: 'Excluded turbine',
    swatch: <span className="h-2.5 w-2.5 rounded-full border-2 border-borderStrong bg-surface2 opacity-50" />
  },
  {
    label: 'Collector route',
    swatch: <span className="h-0.5 w-4 rounded bg-accent" />
  },
  {
    label: 'Reference line / road',
    swatch: (
      <span className="h-0 w-4 border-t-2 border-dashed border-textFaint" />
    )
  },
  {
    label: 'Restricted area',
    swatch: <span className="h-2.5 w-2.5 rounded-[2px] border border-danger bg-danger/30" />
  },
  {
    label: 'Cadastral parcel',
    swatch: <span className="h-2.5 w-2.5 rounded-[2px] border border-textFaint bg-textFaint/20" />
  }
];

export function MapLegend({ onClose }: { onClose: () => void }) {
  return (
    <div className="w-[190px] animate-slide-up rounded-lg border border-borderStrong bg-panel/95 p-2.5 shadow-3 backdrop-blur-sm">
      <div className="mb-2 flex items-center justify-between">
        <h4 className="m-0 text-sm font-bold uppercase tracking-wide text-textMuted">Legend</h4>
        <button
          onClick={onClose}
          aria-label="Hide legend"
          className="-mr-1 flex h-5 w-5 items-center justify-center rounded text-textFaint transition-colors duration-fast ease-out hover:text-text"
        >
          <svg viewBox="0 0 24 24" className="h-3 w-3" fill="none" stroke="currentColor" strokeWidth={2.5} strokeLinecap="round">
            <path d="M18 6 6 18M6 6l12 12" />
          </svg>
        </button>
      </div>
      <ul className="m-0 flex list-none flex-col gap-1.5 p-0">
        {ENTRIES.map((e) => (
          <li key={e.label} className="flex items-center gap-2 text-sm text-textMuted">
            <span className="flex h-3 w-4 flex-none items-center justify-center">{e.swatch}</span>
            {e.label}
          </li>
        ))}
      </ul>
    </div>
  );
}

export function MapLegendToggle() {
  const [open, setOpen] = useState(false);

  if (open) return <MapLegend onClose={() => setOpen(false)} />;

  return (
    <button
      onClick={() => setOpen(true)}
      className="flex h-8 items-center gap-1.5 rounded-lg border border-borderStrong bg-panel/95 px-2.5 text-sm
                 text-textMuted shadow-2 backdrop-blur-sm transition-colors duration-fast ease-out
                 hover:text-text hover:border-textFaint"
    >
      <svg viewBox="0 0 24 24" className="h-3.5 w-3.5" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
        <path d="M4 6h16M4 12h16M4 18h16" />
      </svg>
      Legend
    </button>
  );
}
