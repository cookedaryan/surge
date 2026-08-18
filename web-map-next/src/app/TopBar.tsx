import { ReactNode } from 'react';
import { RunStatusChip } from './RunStatusChip';
import { useUiStore } from '../lib/store';
import { Tooltip } from '../components/ui';

interface TopBarProps {
  projectSlot?: ReactNode;
  actionsSlot?: ReactNode;
}

export function TopBar({ projectSlot, actionsSlot }: TopBarProps) {
  const collapsed = useUiStore((s) => s.sidebarCollapsed);
  const toggleSidebar = useUiStore((s) => s.toggleSidebar);

  return (
    <header className="h-[52px] flex-none flex items-center gap-4 px-3 bg-panel border-b border-border font-ui">
      <Tooltip label={collapsed ? 'Show panel' : 'Hide panel'} side="bottom">
        <button
          onClick={toggleSidebar}
          aria-label={collapsed ? 'Show panel' : 'Hide panel'}
          aria-expanded={!collapsed}
          className="flex h-8 w-8 flex-none items-center justify-center rounded-md text-textFaint
                     transition-colors duration-fast ease-out hover:bg-surface2 hover:text-text"
        >
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
            <rect x="3" y="4" width="18" height="16" rx="2" />
            <path d="M9 4v16" />
          </svg>
        </button>
      </Tooltip>

      <div className="flex items-center gap-2">
        <svg viewBox="0 0 24 24" className="w-[18px] h-[18px] text-accent" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round" strokeLinejoin="round">
          <path d="M13 2 4 14h6l-1 8 9-12h-6l1-8z" />
        </svg>
        <span className="font-bold tracking-wide text-base text-text">SURGE</span>
        <span className="text-sm text-textFaint ml-2 pl-2 border-l border-borderStrong hidden lg:inline">
          Collector &amp; Evacuation Engine
        </span>
      </div>

      <div className="flex items-center gap-2">{projectSlot}</div>
      <RunStatusChip />
      <div className="flex-1" />
      <div className="flex items-center gap-2">{actionsSlot}</div>
    </header>
  );
}
