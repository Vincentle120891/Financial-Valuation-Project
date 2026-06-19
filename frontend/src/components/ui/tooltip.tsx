import React from 'react';
import * as TooltipPrimitive from '@radix-ui/react-tooltip';
import { cn } from '@/lib/utils';

/**
 * Tooltip — Hover tooltip for metadata display.
 * Built on Radix UI Tooltip primitive.
 */

const TooltipProvider = TooltipPrimitive.Provider;
const Tooltip = TooltipPrimitive.Root;
const TooltipTrigger = TooltipPrimitive.Trigger;

const TooltipContent = React.forwardRef<
  React.ComponentRef<typeof TooltipPrimitive.Content>,
  React.ComponentPropsWithoutRef<typeof TooltipPrimitive.Content>
>(({ className, sideOffset = 4, ...props }, ref) => (
  <TooltipPrimitive.Content
    ref={ref}
    sideOffset={sideOffset}
    className={cn(
      'z-50 overflow-hidden rounded-[var(--radius-sm)]',
      'bg-[var(--canvas-surface-elevated)]',
      'border border-[var(--border-default)]',
      'shadow-[var(--shadow-lg)]',
      'px-3 py-1.5',
      'text-[0.75rem] text-[var(--text-primary)]',
      'animate-in fade-in-0 zoom-in-95',
      'data-[state=closed]:animate-out',
      className
    )}
    {...props}
  />
));
TooltipContent.displayName = 'TooltipContent';

export {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
  TooltipProvider,
};
