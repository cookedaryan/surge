import { ReactNode } from 'react';

interface TopBarProps {
  projectSlot?: ReactNode;
  actionsSlot?: ReactNode;
}

export function TopBar({ projectSlot, actionsSlot }: TopBarProps) {
  return (
    <header className="h-[52px] flex-none flex items-center gap-5 px-4 bg-panel border-b border-border font-ui">
      <div className="flex items-center gap-2">
        <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] text-accent" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />
        </svg>
        <span className="font-bold tracking-wide text-sm text-text">SURGE</span>
        <span className="text-[10.5px] text-textFaint ml-2 pl-2 border-l border-borderStrong">
          Collector &amp; Evacuation Engine
        </span>
      </div>
      <div className="flex items-center gap-2">{projectSlot}</div>
      <div className="flex-1" />
      <div className="flex items-center gap-2">{actionsSlot}</div>
    </header>
  );
}
