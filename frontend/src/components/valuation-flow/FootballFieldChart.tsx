import React from 'react';
import {
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ReferenceLine,
  ResponsiveContainer,
  Cell,
} from 'recharts';
import { Card, CardHeader, CardTitle } from '../ui/card';
import { formatSharePrice } from '../../utils/formatters';

/**
 * FootballFieldChart — Valuation Range Synthesis
 *
 * Displays 3 valuation engines as horizontal floating bars showing
 * min/base/max price ranges. Includes a consensus zone overlay and
 * market spot price reference line.
 *
 * Layout: Horizontal bar chart where each row is a methodology.
 * Each bar floats between min and max (invisible base + visible range).
 */

interface ValuationRange {
  method: string;
  label: string;
  low: number;
  base: number;
  high: number;
  color: string;
}

interface FootballFieldChartProps {
  ranges: ValuationRange[];
  marketPrice?: number;
  currency?: string;
}

const METHOD_COLORS: Record<string, string> = {
  DCF: '#3b82f6',     /* Blue 500 */
  DUPONT: '#8b5cf6',  /* Violet 500 */
  COMPS: '#06b6d4',   /* Cyan 500 */
};

/**
 * Calculate the consensus zone (overlap of all ranges)
 */
function calculateConsensusZone(ranges: ValuationRange[]): { min: number; max: number } | null {
  if (ranges.length < 2) return null;
  const consensusMin = Math.max(...ranges.map(r => r.low));
  const consensusMax = Math.min(...ranges.map(r => r.high));
  if (consensusMin >= consensusMax) return null;
  return { min: consensusMin, max: consensusMax };
}

/**
 * Custom floating bar shape
 * Renders a transparent base (from 0 to min) + visible bar (from min to max)
 */
const FloatingBar = (props: any) => {
  const { x, y, width, height, payload, xAxisMap, yAxisMap } = props;
  if (!payload || width <= 0 || height <= 0) return null;

  const method = payload.method;
  const color = METHOD_COLORS[method] || '#64748b';

  return (
    <g>
      <rect
        x={x}
        y={y}
        width={width}
        height={height}
        rx={4}
        fill={color}
        opacity={0.85}
      />
      {/* Base marker (low end) */}
      <rect
        x={x - 1}
        y={y}
        width={3}
        height={height}
        fill={color}
        opacity={0.4}
      />
      {/* High end marker */}
      <rect
        x={x + width - 2}
        y={y}
        width={3}
        height={height}
        fill={color}
        opacity={0.4}
      />
    </g>
  );
};

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div
      className="bg-[var(--canvas-surface)] border border-[var(--border-default)] rounded-lg shadow-[var(--shadow-lg)] p-3"
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      <p className="text-[0.75rem] font-semibold text-[var(--text-primary)] mb-1">{data.label}</p>
      <div className="text-[0.6875rem] text-[var(--text-secondary)] space-y-0.5">
        <p>Low: {formatSharePrice(data.low)}</p>
        <p>Base: {formatSharePrice(data.base)}</p>
        <p>High: {formatSharePrice(data.high)}</p>
      </div>
    </div>
  );
};

const FootballFieldChart: React.FC<FootballFieldChartProps> = ({
  ranges,
  marketPrice,
  currency = 'USD',
}) => {
  // Transform data for Recharts stacked bar (invisible base + visible range)
  const chartData = ranges.map(r => ({
    ...r,
    invisibleBase: r.low,
    rangeSpread: r.high - r.low,
  }));

  // Calculate chart domain
  const allPrices = ranges.flatMap(r => [r.low, r.high]);
  if (marketPrice) allPrices.push(marketPrice);
  const minPrice = Math.min(...allPrices);
  const maxPrice = Math.max(...allPrices);
  const padding = (maxPrice - minPrice) * 0.15;

  const consensus = calculateConsensusZone(ranges);

  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-[0.875rem]">Valuation Ranges</CardTitle>
      </CardHeader>
      <div style={{ width: '100%', height: 170 }}>
        <ResponsiveContainer>
          <BarChart
            data={chartData}
            layout="vertical"
            margin={{ top: 5, right: 20, bottom: 5, left: 10 }}
          >
            <CartesianGrid
              strokeDasharray="3 3"
              stroke="var(--border-subtle)"
              horizontal={false}
            />
            <XAxis
              type="number"
              domain={[minPrice - padding, maxPrice + padding]}
              tickFormatter={(v: number) => formatSharePrice(v, currency as any)}
              tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
              axisLine={{ stroke: 'var(--border-default)' }}
              tickLine={false}
            />
            <YAxis
              type="category"
              dataKey="method"
              width={70}
              tick={{ fontSize: 11, fontWeight: 600, fill: 'var(--text-secondary)' }}
              axisLine={false}
              tickLine={false}
            />
            <Tooltip content={<CustomTooltip />} />
            {/* Invisible base bar */}
            <Bar
              dataKey="invisibleBase"
              stackId="a"
              fill="transparent"
              isAnimationActive={false}
            />
            {/* Visible range bar */}
            <Bar
              dataKey="rangeSpread"
              stackId="a"
              shape={<FloatingBar />}
              isAnimationActive={true}
              animationDuration={800}
            />
          </BarChart>
        </ResponsiveContainer>
      </div>

      {/* Consensus Zone Legend */}
      {consensus && (
        <div className="mt-2 text-[0.6875rem] text-[var(--text-tertiary)] flex items-center gap-2">
          <span
            className="inline-block w-3 h-3 rounded-sm"
            style={{ background: 'rgba(99, 102, 241, 0.15)' }}
          />
          Consensus Zone: {formatSharePrice(consensus.min)} — {formatSharePrice(consensus.max)}
        </div>
      )}
    </Card>
  );
};

export default FootballFieldChart;
