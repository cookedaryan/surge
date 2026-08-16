import { Dialog } from './Dialog';
import { Button } from './Button';

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  /** What will happen, in plain terms. Name the account or object by name, not "this item". */
  body: string;
  confirmLabel: string;
  onConfirm: () => void;
  onCancel: () => void;
}

/**
 * Asks before an action that takes effect immediately and cannot be undone by pressing back.
 *
 * <p>Account changes used to apply on the first click — and since the authentication filter now
 * resolves every token against its account, suspending someone or changing their role logs them
 * out or re-scopes them within a second rather than whenever their token happened to expire. That
 * made an accidental click much more consequential than it used to be.
 */
export function ConfirmDialog({ open, title, body, confirmLabel, onConfirm, onCancel }: ConfirmDialogProps) {
  return (
    <Dialog
      open={open}
      onOpenChange={(next) => {
        if (!next) onCancel();
      }}
      title={title}
      widthClassName="w-[380px]"
      footer={
        <>
          <Button size="sm" onClick={onCancel}>
            Cancel
          </Button>
          <Button size="sm" variant="danger" onClick={onConfirm}>
            {confirmLabel}
          </Button>
        </>
      }
    >
      <p className="m-0 text-[11.5px] leading-relaxed text-textFaint">{body}</p>
    </Dialog>
  );
}
