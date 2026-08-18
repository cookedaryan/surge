import { ButtonHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';
import { Spinner } from './Spinner';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary' | 'danger' | 'ghost' | 'subtle';
  size?: 'default' | 'sm' | 'icon';
  /** Shows a spinner and blocks interaction without collapsing the button's width. */
  loading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', loading = false, disabled, children, ...props }, ref) => (
    <button
      ref={ref}
      // A loading button is genuinely unavailable, so it reports that to assistive tech rather than
      // merely looking busy — and it stops a second submit landing while the first is in flight.
      disabled={disabled || loading}
      aria-busy={loading || undefined}
      className={clsx(
        'relative inline-flex items-center justify-center gap-1.5 rounded-md border font-semibold cursor-pointer',
        'transition-[background-color,border-color,color,transform,box-shadow] duration-fast ease-out',
        // Both sizes clear the 24px minimum WCAG 2.5.8 asks for; the default is 32px so the
        // toolbar is comfortable rather than merely compliant.
        size === 'default' && 'h-8 px-3 text-sm',
        size === 'sm' && 'h-7 px-2.5 text-sm',
        size === 'icon' && 'h-8 w-8 p-0',
        variant === 'primary' && 'bg-accent border-accent text-accentInk hover:bg-accent400 hover:border-accent400 active:bg-accent600 active:border-accent600',
        // Reserved for the button that actually performs a destructive action, so confirming one
        // never looks like an ordinary click.
        variant === 'danger' && 'bg-danger border-danger text-white hover:brightness-110 active:brightness-95',
        variant === 'default' && 'bg-surface2 border-borderStrong text-text hover:bg-surface3 hover:border-textFaint',
        variant === 'subtle' && 'bg-transparent border-border text-textMuted hover:bg-surface2 hover:text-text hover:border-borderStrong',
        variant === 'ghost' && 'bg-transparent border-transparent text-textMuted hover:bg-surface2 hover:text-text',
        // Pressed feedback. Suppressed while disabled so a dead control never appears to respond.
        !disabled && !loading && 'active:scale-[0.98]',
        'disabled:opacity-50 disabled:cursor-not-allowed disabled:active:scale-100',
        className
      )}
      {...props}
    >
      {/* The label keeps its space while loading rather than being swapped out, so the button does
          not resize mid-click and shift whatever sits beside it.
          Hidden with opacity rather than `visibility`, which would take the label out of the
          accessibility tree and leave the button with no accessible name for the whole request. */}
      <span className={clsx('inline-flex items-center gap-1.5', loading && 'opacity-0')}>{children}</span>
      {loading && (
        <span className="absolute inset-0 inline-flex items-center justify-center">
          <Spinner className="w-3.5 h-3.5" />
        </span>
      )}
    </button>
  )
);
Button.displayName = 'Button';
