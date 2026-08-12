import { ButtonHTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'default' | 'primary';
  size?: 'default' | 'sm';
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ className, variant = 'default', size = 'default', ...props }, ref) => (
    <button
      ref={ref}
      className={clsx(
        'inline-flex items-center gap-1.5 rounded-md border font-semibold cursor-pointer transition-colors',
        size === 'default' ? 'h-7 px-2.5 text-xs' : 'h-[26px] px-2 text-[11.5px]',
        variant === 'primary'
          ? 'bg-accent border-accent text-white hover:brightness-110'
          : 'bg-surface2 border-borderStrong text-text hover:border-textFaint',
        'disabled:opacity-50 disabled:cursor-not-allowed',
        className
      )}
      {...props}
    />
  )
);
Button.displayName = 'Button';
