import React from 'react';
import { cn } from '@/lib/utils';

/**
 * DataTable — Structured financial data table component.
 * Enforces tabular-nums, token-backed borders, and consistent spacing.
 */

const Table = React.forwardRef<
  HTMLTableElement,
  React.HTMLAttributes<HTMLTableElement>
>(({ className, ...props }, ref) => (
  <div className="relative w-full overflow-auto">
    <table
      ref={ref}
      className={cn(
        'w-full caption-bottom text-[0.75rem]',
        '[&_td]:border-b [&_td]:border-[var(--border-default)]',
        '[&_th]:border-b [&_th]:border-[var(--border-default)]',
        className
      )}
      style={{ fontVariantNumeric: 'tabular-nums lining-nums', fontFeatureSettings: '"tnum" on, "lnum" on' }}
      {...props}
    />
  </div>
));
Table.displayName = 'Table';

const TableHeader = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <thead
    ref={ref}
    className={cn('[&_tr]:border-b', className)}
    {...props}
  />
));
TableHeader.displayName = 'TableHeader';

const TableBody = React.forwardRef<
  HTMLTableSectionElement,
  React.HTMLAttributes<HTMLTableSectionElement>
>(({ className, ...props }, ref) => (
  <tbody
    ref={ref}
    className={cn('[&_tr:last-child]:border-0', className)}
    {...props}
  />
));
TableBody.displayName = 'TableBody';

const TableRow = React.forwardRef<
  HTMLTableRowElement,
  React.HTMLAttributes<HTMLTableRowElement>
>(({ className, ...props }, ref) => (
  <tr
    ref={ref}
    className={cn(
      'border-b border-[var(--border-default)]',
      'transition-colors hover:bg-[var(--border-subtle)]',
      'data-[state=selected]:bg-[var(--accent-primary-subtle)]',
      className
    )}
    {...props}
  />
));
TableRow.displayName = 'TableRow';

const TableHead = React.forwardRef<
  HTMLTableCellElement,
  React.ThHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <th
    ref={ref}
    className={cn(
      'h-7 px-2.5 py-1.5',
      'text-left align-middle',
      'text-[0.625rem] font-medium',
      'uppercase tracking-wider',
      'text-[var(--text-tertiary)]',
      '[&[role=checkbox]]:translate-y-[2px]',
      className
    )}
    style={{ fontVariantNumeric: 'tabular-nums lining-nums', fontFeatureSettings: '"tnum" on, "lnum" on' }}
    {...props}
  />
));
TableHead.displayName = 'TableHead';

const TableCell = React.forwardRef<
  HTMLTableCellElement,
  React.TdHTMLAttributes<HTMLTableCellElement>
>(({ className, ...props }, ref) => (
  <td
    ref={ref}
    className={cn(
      'px-2.5 py-1.5',
      'align-middle',
      'text-[0.75rem]',
      'text-[var(--text-primary)]',
      '[&[role=checkbox]]:translate-y-[2px]',
      className
    )}
    style={{ fontVariantNumeric: 'tabular-nums lining-nums', fontFeatureSettings: '"tnum" on, "lnum" on' }}
    {...props}
  />
));
TableCell.displayName = 'TableCell';

const TableCaption = React.forwardRef<
  HTMLTableCaptionElement,
  React.HTMLAttributes<HTMLTableCaptionElement>
>(({ className, ...props }, ref) => (
  <caption
    ref={ref}
    className={cn(
      'mt-2 text-[0.6875rem] text-[var(--text-tertiary)]',
      className
    )}
    {...props}
  />
));
TableCaption.displayName = 'TableCaption';

export {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
  TableCell,
  TableCaption,
};
