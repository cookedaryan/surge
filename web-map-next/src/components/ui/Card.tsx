import { HTMLAttributes, forwardRef, ReactNode } from 'react';
import clsx from 'clsx';

interface CardProps extends HTMLAttributes<HTMLDivElement> {
  /** Adds hover elevation. Only for cards that are themselves a control. */
  interactive?: boolean;
  tone?: 'default' | 'danger' | 'success' | 'accent';
}

const TONE: Record<string, string> = {
  default: 'border-border',
  danger: 'border-danger/50 bg-danger/[0.04]',
  success: 'border-success/40 bg-success/[0.04]',
  accent: 'border-accent/40 bg-accent100'
};

export const Card = forwardRef<HTMLDivElement, CardProps>(
  ({ className, interactive, tone = 'default', ...props }, ref) => (
    <div
      ref={ref}
      className={clsx(
        'bg-surface border rounded-lg p-3 transition-[border-color,box-shadow,transform] duration-fast ease-out',
        TONE[tone],
        interactive && 'cursor-pointer hover:border-borderStrong hover:shadow-2 hover:-translate-y-px',
        className
      )}
      {...props}
    />
  )
);
Card.displayName = 'Card';

interface CardTitleProps extends HTMLAttributes<HTMLHeadingElement> {
  icon?: ReactNode;
  /** Rendered at the far right of the title row — a count, a status pill, a control. */
  aside?: ReactNode;
}

export function CardTitle({ className, icon, aside, children, ...props }: CardTitleProps) {
  return (
    <h3
      className={clsx(
        // The uppercase is load-bearing beyond styling: the Playwright suite matches rendered text,
        // so `getByText('WHY THIS ROUTE')` binds to this rule rather than to the source string.
        'm-0 mb-2 text-sm font-bold uppercase tracking-wide text-textMuted flex items-center gap-1.5',
        className
      )}
      {...props}
    >
      {icon && <span className="text-textFaint [&>svg]:w-3.5 [&>svg]:h-3.5">{icon}</span>}
      {children}
      {aside && <span className="ml-auto font-normal normal-case tracking-normal">{aside}</span>}
    </h3>
  );
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={clsx('m-0 mb-2.5 text-sm text-textFaint leading-relaxed', className)} {...props} />;
}
