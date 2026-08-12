import { HTMLAttributes, forwardRef } from 'react';
import clsx from 'clsx';

export const Card = forwardRef<HTMLDivElement, HTMLAttributes<HTMLDivElement>>(
  ({ className, ...props }, ref) => (
    <div ref={ref} className={clsx('bg-surface border border-border rounded-lg p-3', className)} {...props} />
  )
);
Card.displayName = 'Card';

export function CardTitle({ className, ...props }: HTMLAttributes<HTMLHeadingElement>) {
  return (
    <h3
      className={clsx(
        'm-0 mb-2 text-[11.5px] font-bold uppercase tracking-wide text-textMuted flex items-center gap-1.5',
        className
      )}
      {...props}
    />
  );
}

export function CardDescription({ className, ...props }: HTMLAttributes<HTMLParagraphElement>) {
  return <p className={clsx('m-0 mb-2.5 text-[11.5px] text-textFaint leading-relaxed', className)} {...props} />;
}
