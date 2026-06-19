import React from 'react';
import { cn } from '@/lib/utils';
import { cva, type VariantProps } from 'class-variance-authority';

/**
 * Badge — Status indicator for data quality.
 * Replaces inline badge styles in DataFieldDisplay.jsx.
 */

const badgeVariants = cva(
  'inline-flex items-center rounded-md px-2 py-0.5 text-[0.6875rem] font-medium tracking-wide whitespace-nowrap',
  {
    variants: {
      variant: {
        retrieved:
          'bg-[var(--color-bullish-bg)] text-[var(--color-bullish)]',
        calculated:
          'bg-[var(--accent-primary-subtle)] text-[var(--accent-primary)]',
        ai:
          'bg-[var(--color-neutral-bg)] text-[var(--color-ai)]',
        manual:
          'bg-[var(--accent-primary-subtle)] text-[var(--color-manual)]',
        missing:
          'bg-[var(--color-neutral-bg)] text-[var(--color-neutral)]',
        default:
          'bg-[var(--border-subtle)] text-[var(--text-secondary)]',
        primary:
          'bg-[var(--accent-primary-subtle)] text-[var(--accent-primary)]',
      },
    },
    defaultVariants: {
      variant: 'default',
    },
  }
);

export interface BadgeProps
  extends React.HTMLAttributes<HTMLDivElement>,
    VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return (
    <div className={cn(badgeVariants({ variant }), className)} {...props} />
  );
}

export { Badge, badgeVariants };
