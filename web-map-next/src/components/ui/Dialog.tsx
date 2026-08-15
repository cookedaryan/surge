import * as RadixDialog from '@radix-ui/react-dialog';
import { ReactNode } from 'react';

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  title: string;
  children: ReactNode;
  footer?: ReactNode;
  widthClassName?: string;
}

export function Dialog({ open, onOpenChange, title, children, footer, widthClassName = 'w-[480px]' }: DialogProps) {
  return (
    <RadixDialog.Root open={open} onOpenChange={onOpenChange}>
      <RadixDialog.Portal>
        <RadixDialog.Overlay className="fixed inset-0 bg-black/60 z-[9990]" />
        <RadixDialog.Content
          className={`fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 ${widthClassName} max-w-[92vw] max-h-[85vh] overflow-y-auto bg-panel border border-borderStrong rounded-lg p-4 z-[10000] font-ui text-text`}
        >
          <RadixDialog.Title className="m-0 mb-3 text-[13.5px] font-bold text-text">{title}</RadixDialog.Title>
          {children}
          {footer && <div className="mt-4 flex justify-end gap-2">{footer}</div>}
        </RadixDialog.Content>
      </RadixDialog.Portal>
    </RadixDialog.Root>
  );
}
