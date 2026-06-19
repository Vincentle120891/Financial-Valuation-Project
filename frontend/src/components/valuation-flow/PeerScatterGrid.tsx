import React, { useMemo } from 'react';
import {
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer,
  ReferenceLine,
  Cell,
  Label,
} from 'recharts';
import { Card, CardHeader, CardTitle } from '../ui/card';
import { formatPercent, formatMultiple } from '../../utils/formatters';

/**
 * PeerScatterGrid — Cross-Sectional Multiples Matrix
 *
 * Four-quadrant scatter plot contextualizing the target company's
 * operational efficiency against peer valuation multiples.
 *
 * Quadrants:
 * 1. Top-Left: Overvalued Underperformers
 * 2. Top-Right: Premium Leaders
 * 3. Bottom-Left: Value Traps
 * 4. Bottom-Right: Acquisition Target Alpha Zone
 */

interface PeerNode {
  ticker: string;
  x: number;
  y: number;
  isTarget?: boolean;
}

interface PeerScatterGridProps {
  peers: PeerNode[];
  xLabel?: string;
  yLabel?: string;
  targetTicker?: string;
}

function calculateMedian(values: number[]): number {
  const sorted = [...values].sort((a, b) => a - b);
  const mid = Math.floor(sorted.length / 2);
  return sorted.length % 2 !== 0
    ? sorted[mid]
    : (sorted[mid - 1] + sorted[mid]) / 2;
}

const ScatterTooltip = ({ active, payload }: any) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div
      className="bg-[var(--canvas-surface)] border border-[var(--border-default)] rounded-lg shadow-[var(--shadow-lg)] p-3"
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      <p className="text-[0.75rem] font-semibold text-[var(--text-primary)] mb-1">
        {data.ticker}
        {data.isTarget && (
          <span className="ml-1 text-[0.625rem] text-[var(--accent-primary)]">(Target)</span>
        )}
      </p>
      <div className="text-[0.6875rem] text-[var(--text-secondary)] space-y-0.5">
        <p>Efficiency: {data.x.toFixed(1)}%</p>
        <p>Multiple: {data.y.toFixed(1)}x</p>
      </div>
    </div>
  );
};

const PeerScatterGrid: React.FC<PeerScatterGridProps> = ({
  peers,
  xLabel = 'EBITDA Margin (%)',
  yLabel = 'EV/EBITDA',
  targetTicker,
}) => {
  const { medianX, medianY, xDomain, yDomain } = useMemo(() => {
    if (peers.length === 0) {
      return { medianX: 0, medianY: 0, xDomain: [0, 100], yDomain: [0, 50] };
    }
    const xVals = peers.map(p => p.x);
    const yVals = peers.map(p => p.y);
    const mx = calculateMedian(xVals);
    const my = calculateMedian(yVals);
    const xMin = Math.min(...xVals) - 5;
    const xMax = Math.max(...xVals) + 5;
    const yMin = Math.min(...yVals) - 2;
    const yMax = Math.max(...yVals) + 2;
    return { medianX: mx, medianY: my, xDomain: [xMin, xMax], yDomain: [yMin, yMax] };
  }, [peers]);

  if (peers.length === 0) {
    return (
      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-[0.875rem]">Peer Comparison</CardTitle>
        </CardHeader>
        <div className="flex items-center justify-center h-[200px] text-[0.75rem] text-[var(--text-tertiary)]">
          No peer data available
        </div>
      </Card>
    );
  }

  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-[0.875rem]">Peer Comparison</CardTitle>
      </CardHeader>
      <div style={{ width: '100%', height: 160 }}>
        <ResponsiveContainer>
          <ScatterChart margin={{ top: 10, right: 10, bottom: 10, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
            <XAxis
              type="number"
              dataKey="x"
              domain={xDomain}
              name={xLabel}
              tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
              axisLine={{ stroke: 'var(--border-default)' }}
              tickLine={false}
            >
              <Label
                value={xLabel}
                position="bottom"
                offset={-2}
                style={{ fontSize: 9, fill: 'var(--text-tertiary)' }}
              />
            </XAxis>
            <YAxis
              type="number"
              dataKey="y"
              domain={yDomain}
              name={yLabel}
              tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
              axisLine={{ stroke: 'var(--border-default)' }}
              tickLine={false}
              width={35}
            >
              <Label
                value={yLabel}
                angle={-90}
                position="insideLeft"
                offset={10}
                style={{ fontSize: 9, fill: 'var(--text-tertiary)' }}
              />
            </YAxis>
            <Tooltip content={<ScatterTooltip />} />
            {/* Median crosshairs */}
            <ReferenceLine
              x={medianX}
              stroke="var(--text-tertiary)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            <ReferenceLine
              y={medianY}
              stroke="var(--text-tertiary)"
              strokeDasharray="4 4"
              strokeWidth={1}
            />
            {/* Peer nodes (grey) */}
            <Scatter name="Peers" data={peers.filter(p => !p.isTarget)}>
              {peers.filter(p => !p.isTarget).map((entry, idx) => (
                <Cell
                  key={`peer-${idx}`}
                  fill="var(--text-tertiary)"
                  opacity={0.5}
                  r={4}
                />
              ))}
            </Scatter>
            {/* Target node (blue, highlighted) */}
            {peers.some(p => p.isTarget) && (
              <Scatter name="Target" data={peers.filter(p => p.isTarget)}>
                {peers.filter(p => p.isTarget).map((entry, idx) => (
                  <Cell
                    key={`target-${idx}`}
                    fill="var(--accent-primary)"
                    stroke="var(--canvas-surface)"
                    strokeWidth={2}
                    r={7}
                  />
                ))}
              </Scatter>
            )}
          </ScatterChart>
        </ResponsiveContainer>
      </div>

      {/* Quadrant legend */}
      <div className="mt-2 grid grid-cols-2 gap-1 text-[0.5625rem] text-[var(--text-tertiary)]">
        <span>↑ High Multiple</span>
        <span className="text-right">Premium Leaders →</span>
        <span>Overvalued Underperformers</span>
        <span className="text-right">Alpha Zone →</span>
        <span>← Value Traps</span>
        <span className="text-right">← Strong Efficiency</span>
      </div>
    </Card>
  );
};

export default PeerScatterGrid;
