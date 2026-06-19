import React from 'react';
import { cn } from '@/lib/utils';

/**
 * Skeleton — Base shimmer loading placeholder.
 * Uses Tailwind animate-pulse with token-backed background colors.
 */

interface SkeletonProps extends React.HTMLAttributes<HTMLDivElement> {
  variant?: 'bar' | 'circle' | 'rect' | 'card';
  width?: string;
  height?: string;
}

const variantClasses: Record<string, string> = {
  bar: 'h-3 rounded-md',
  circle: 'rounded-full',
  rect: 'rounded-lg',
  card: 'rounded-xl h-48',
};

const Skeleton: React.FC<SkeletonProps> = ({
  variant = 'bar',
  width,
  height,
  className,
  style,
  ...props
}) => (
  <div
    className={cn(
      'animate-pulse',
      'bg-[var(--border-default)]',
      variantClasses[variant],
      className
    )}
    style={{
      width: width || '100%',
      height: height || undefined,
      ...style,
    }}
    {...props}
  />
);

/**
 * StepSkeleton — Full step loading skeleton.
 * Displays a shimmer layout matching the general step structure.
 */
interface StepSkeletonProps {
  showHeader?: boolean;
  rows?: number;
  showChart?: boolean;
}

const StepSkeleton: React.FC<StepSkeletonProps> = ({
  showHeader = true,
  rows = 5,
  showChart = false,
}) => (
  <div className="step-container animate-pulse space-y-4">
    {showHeader && (
      <div className="space-y-2">
        <Skeleton variant="bar" height="24px" width="60%" />
        <Skeleton variant="bar" height="14px" width="80%" />
      </div>
    )}
    {Array.from({ length: rows }).map((_, i) => (
      <div key={i} className="flex items-center gap-3">
        <Skeleton variant="bar" height="12px" width="30%" />
        <Skeleton variant="bar" height="12px" width="20%" />
        <Skeleton variant="bar" height="12px" width="15%" />
      </div>
    ))}
    {showChart && (
      <Skeleton variant="rect" height="200px" />
    )}
  </div>
);

/**
 * DataFieldSkeleton — Shimmer for a single data field display.
 */
const DataFieldSkeleton: React.FC = () => (
  <div className="p-3 bg-[var(--border-subtle)] rounded-lg space-y-2 animate-pulse">
    <div className="flex justify-between">
      <Skeleton variant="bar" height="12px" width="40%" />
      <Skeleton variant="bar" height="14px" width="20%" />
    </div>
    <Skeleton variant="bar" height="10px" width="30%" />
  </div>
);

export { Skeleton, StepSkeleton, DataFieldSkeleton };
export type { SkeletonProps, StepSkeletonProps };
