import * as RadixDialog from '@radix-ui/react-dialog';
import { ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  description?: string;
  children: ReactNode;
  footer?: ReactNode;
  widthClassName?: string;
}

export function Dialog({
  open,
  onOpenChange,
  title,
  description,
  children,
  footer,
  widthClassName = 'w-[480px]'
}: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        {/* Radix holds the element mounted until its exit animation ends, which is what lets the
            dialog fade out instead of being torn off the screen. That only works while the
            animation has a non-zero duration — hence the 0.01ms floor in the reduced-motion
            override rather than 0s. */}
        <RadixDialog.Overlay className="fixed inset-0 bg-black/65 z-[9990] data-[state=open]:animate-fade-in data-[state=closed]:animate-fade-out" />
        <RadixDialog.Content
          className={`fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 ${widthClassName} max-w-[92vw] max-h-[85vh] overflow-y-auto
                      bg-panel border border-borderStrong rounded-lg shadow-3 p-4 z-[10000] font-ui text-text
                      data-[state=open]:animate-scale-in data-[state=closed]:animate-scale-out`}
        >
          <div className="flex items-start gap-3 mb-3">
            <div className="min-w-0 flex-1">
              <RadixDialog.Title className="m-0 text-base font-bold text-text">{title}</RadixDialog.Title>
              {description && (
                <RadixDialog.Description className="m-0 mt-1 text-sm text-textFaint">{description}</RadixDialog.Description>
              )}
            </div>
            <RadixDialog.Close
              aria-label="Close"
              className="flex-none -mt-0.5 -mr-0.5 w-7 h-7 inline-flex items-center justify-center rounded-md text-textFaint
                         hover:text-text hover:bg-surface2 transition-colors duration-fast ease-out"
            >
              <svg viewBox="0 0 24 24" className="w-4 h-4" fill="none" stroke="currentColor" strokeWidth={2} strokeLinecap="round">
                <path d="M18 6 6 18M6 6l12 12" />
              </svg>
            </RadixDialog.Close>
          </div>
          {children}
          {footer && <div className="mt-4 flex justify-end gap-2">{footer}</div>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
