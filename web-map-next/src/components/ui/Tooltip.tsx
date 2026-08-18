import * as RadixTooltip from '@radix-ui/react-tooltip';
import { ReactNode } from 'react';

export function TooltipProvider({ children }: { children: ReactNode }) {
  return (
    <RadixTooltip.Provider delayDuration={350} skipDelayDuration={200}>
      {children}
    </RadixTooltip.Provider>
  );
}

interface TooltipProps {
  label: string;
  children: ReactNode;
  side?: 'top' | 'right' | 'bottom' | 'left';
}

/**
 * Hover/focus label for controls whose meaning is otherwise carried by an icon alone.
 *
 * <p>Deliberately not a replacement for an accessible name. The trigger still needs its own
 * `aria-label`: a tooltip is announced only once the control has focus, which is too late for
 * someone scanning the rail with a screen reader, and never for a touch user.
 */
export function Tooltip({ label, children, side = 'right' }: TooltipProps) {
  return (
    <RadixTooltip.Root>
      <RadixTooltip.Trigger asChild>{children}</RadixTooltip.Trigger>
      <RadixTooltip.Portal>
        <RadixTooltip.Content
          side={side}
          sideOffset={8}
          className="z-[10050] rounded-md border border-borderStrong bg-surface3 px-2 py-1 text-sm text-text shadow-2
                     data-[state=delayed-open]:animate-fade-in data-[state=closed]:animate-fade-out"
        >
          {label}
          <RadixTooltip.Arrow className="fill-[var(--surface-3)]" />
        </RadixTooltip.Content>
      </RadixTooltip.Portal>
    </RadixTooltip.Root>
  );
}
