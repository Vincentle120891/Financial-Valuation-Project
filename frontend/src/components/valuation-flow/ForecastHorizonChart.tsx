import React from 'react';
import {
  ComposedChart,
  Bar,
  Area,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  ReferenceLine,
} from 'recharts';
import { Card, CardHeader, CardTitle } from '../ui/card';
import { formatScaleLabel, formatPercent } from '../../utils/formatters';

/**
 * ForecastHorizonChart — Discrete Projection Timeline
 *
 * Dual-axis composed bar and area chart showing historical trends
 * alongside forecasted projections over a 5-10 year window.
 */

interface PeriodData {
  period: string;
  revenue?: number;
  fcf?: number;
  margin?: number;
  isForecast?: boolean;
}

interface ForecastHorizonChartProps {
  historicalPeriods?: PeriodData[];
  forecastPeriods?: PeriodData[];
  lastHistoricalPeriod?: string;
  currency?: string;
}

const CustomTooltip = ({ active, payload, label }: any) => {
  if (!active || !payload || !payload.length) return null;
  const data = payload[0]?.payload;
  if (!data) return null;

  return (
    <div
      className="bg-[var(--canvas-surface)] border border-[var(--border-default)] rounded-lg shadow-[var(--shadow-lg)] p-3"
      style={{ fontVariantNumeric: 'tabular-nums' }}
    >
      <p className="text-[0.75rem] font-semibold text-[var(--text-primary)] mb-1">
        {label}
        {data.isForecast && (
          <span className="ml-1 text-[0.625rem] text-[var(--color-ai)] font-normal">(Forecast)</span>
        )}
      </p>
      <div className="text-[0.6875rem] text-[var(--text-secondary)] space-y-0.5">
        {data.revenue != null && (
          <p>Revenue: {formatScaleLabel(data.revenue)}</p>
        )}
        {data.fcf != null && (
          <p>FCF: {formatScaleLabel(data.fcf)}</p>
        )}
        {data.margin != null && (
          <p>Margin: {formatPercent(data.margin / 100)}</p>
        )}
      </div>
    </div>
  );
};

const ForecastHorizonChart: React.FC<ForecastHorizonChartProps> = ({
  historicalPeriods = [],
  forecastPeriods = [],
  lastHistoricalPeriod,
  currency = 'USD',
}) => {
  const allData: PeriodData[] = [
    ...historicalPeriods.map(p => ({ ...p, isForecast: false })),
    ...forecastPeriods.map(p => ({ ...p, isForecast: true })),
  ];

  if (allData.length === 0) {
    return (
      <Card className="p-4">
        <CardHeader className="p-0 pb-3">
          <CardTitle className="text-[0.875rem]">Forecast Horizon</CardTitle>
        </CardHeader>
        <div className="flex items-center justify-center h-[200px] text-[0.75rem] text-[var(--text-tertiary)]">
          No forecast data available
        </div>
      </Card>
    );
  }

  const separatorPeriod = lastHistoricalPeriod || historicalPeriods[historicalPeriods.length - 1]?.period;

  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-[0.875rem]">Forecast Horizon</CardTitle>
      </CardHeader>
      <div style={{ width: '100%', height: 160 }}>
        <ResponsiveContainer>
          <ComposedChart data={allData} margin={{ top: 5, right: 10, bottom: 5, left: 10 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--border-subtle)" />
            <XAxis
              dataKey="period"
              tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
              axisLine={{ stroke: 'var(--border-default)' }}
              tickLine={false}
            />
            <YAxis
              yAxisId="revenue"
              orientation="left"
              tickFormatter={(v: number) => formatScaleLabel(v)}
              tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <YAxis
              yAxisId="fcf"
              orientation="right"
              tickFormatter={(v: number) => formatScaleLabel(v)}
              tick={{ fontSize: 10, fill: 'var(--text-tertiary)' }}
              axisLine={false}
              tickLine={false}
              width={50}
            />
            <Tooltip content={<CustomTooltip />} />
            <Legend
              wrapperStyle={{ fontSize: 10, color: 'var(--text-secondary)' }}
            />
            {/* Revenue bars */}
            <Bar
              yAxisId="revenue"
              dataKey="revenue"
              name="Revenue"
              fill="var(--accent-primary)"
              opacity={0.7}
              radius={[2, 2, 0, 0]}
              barSize={20}
            />
            {/* FCF area */}
            <Area
              yAxisId="fcf"
              type="monotone"
              dataKey="fcf"
              name="Free Cash Flow"
              stroke="var(--color-bullish)"
              fill="var(--color-bullish-bg)"
              strokeWidth={2}
            />
            {/* Historical/Forecast separator line */}
            {separatorPeriod && (
              <ReferenceLine
                yAxisId="revenue"
                x={separatorPeriod}
                stroke="var(--accent-primary)"
                strokeDasharray="4 4"
                strokeWidth={2}
                label={{
                  value: 'Forecast →',
                  position: 'insideTopRight',
                  fontSize: 9,
                  fill: 'var(--accent-primary)',
                }}
              />
            )}
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    </Card>
  );
};

export default ForecastHorizonChart;
