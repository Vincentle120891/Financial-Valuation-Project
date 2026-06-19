import React from 'react';
import { Card, CardHeader, CardTitle } from '../ui/card';
import { formatSharePrice } from '../../utils/formatters';

/**
 * SensitivityHeatmap — Variable Risk Grid
 *
 * Interactive HTML table mapping how changes in WACC and Terminal Growth Rate
 * alter the final DCF price. Cells are color-coded based on their deviation
 * from the current market price (green = upside, red = downside).
 *
 * Uses the Table component from ui/table.tsx for consistent styling.
 */

interface SensitivityData {
  waccValues: number[];        // Column headers (e.g., [7.5, 8.0, 8.5, 9.0, 9.5])
  tgrValues: number[];         // Row headers (e.g., [1.5, 1.75, 2.0, 2.25, 2.5])
  prices: number[][];          // prices[row][col] — the implied share price
  baseCaseRow: number;         // Index of base case TGR
  baseCaseCol: number;         // Index of base case WACC
}

interface SensitivityHeatmapProps {
  data: SensitivityData;
  marketPrice?: number;
  currency?: string;
}

/**
 * Calculate heatmap color based on variance from market price.
 * Green tint for upside, red tint for downside.
 */
function getHeatmapColor(price: number, marketPrice: number): string {
  const variance = (price - marketPrice) / marketPrice;
  if (variance > 0) {
    // Progressive emerald green
    const intensity = Math.min(variance * 5, 1);
    return `rgba(5, 150, 105, ${0.06 + intensity * 0.35})`;
  } else {
    // Progressive red
    const intensity = Math.min(Math.abs(variance) * 5, 1);
    return `rgba(220, 38, 38, ${0.06 + intensity * 0.35})`;
  }
}

/**
 * Determine text color for contrast protection.
 * White text on saturated backgrounds, default on light ones.
 */
function getTextColor(price: number, marketPrice: number): string {
  const intensity = Math.min(Math.abs((price - marketPrice) / marketPrice) * 5, 1);
  return intensity > 0.5 ? '#ffffff' : 'var(--text-primary)';
}

const SensitivityHeatmap: React.FC<SensitivityHeatmapProps> = ({
  data,
  marketPrice,
  currency = 'USD',
}) => {
  const { waccValues, tgrValues, prices, baseCaseRow, baseCaseCol } = data;

  return (
    <Card className="p-4">
      <CardHeader className="p-0 pb-3">
        <CardTitle className="text-[0.875rem]">Sensitivity Matrix</CardTitle>
      </CardHeader>
      <div className="overflow-x-auto">
        <table
          className="w-full border-collapse text-center"
          style={{ fontVariantNumeric: 'tabular-nums' }}
        >
          <thead>
            <tr>
              <th className="px-2 py-1 text-[0.625rem] font-medium text-[var(--text-tertiary)] uppercase tracking-wider">
                WACC →<br />TGR ↓
              </th>
              {waccValues.map((wacc, colIdx) => (
                <th
                  key={colIdx}
                  className={`px-2 py-1 text-[0.625rem] font-medium uppercase tracking-wider ${
                    colIdx === baseCaseCol
                      ? 'text-[var(--accent-primary)] font-bold'
                      : 'text-[var(--text-tertiary)]'
                  }`}
                >
                  {wacc.toFixed(1)}%
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {tgrValues.map((tgr, rowIdx) => (
              <tr key={rowIdx}>
                <td
                  className={`px-2 py-1 text-[0.625rem] font-medium uppercase tracking-wider ${
                    rowIdx === baseCaseRow
                      ? 'text-[var(--accent-primary)] font-bold'
                      : 'text-[var(--text-tertiary)]'
                  }`}
                >
                  {tgr.toFixed(2)}%
                </td>
                {prices[rowIdx]?.map((price, colIdx) => {
                  const isBaseCase = rowIdx === baseCaseRow && colIdx === baseCaseCol;
                  const bgColor = marketPrice
                    ? getHeatmapColor(price, marketPrice)
                    : 'transparent';
                  const textColor = marketPrice
                    ? getTextColor(price, marketPrice)
                    : 'var(--text-primary)';

                  return (
                    <td
                      key={colIdx}
                      className="px-2 py-1.5 text-[0.6875rem] font-medium relative"
                      style={{
                        backgroundColor: bgColor,
                        color: textColor,
                        border: isBaseCase
                          ? '2px solid var(--accent-primary)'
                          : '1px solid var(--border-subtle)',
                        fontWeight: isBaseCase ? 700 : 500,
                      }}
                    >
                      {formatSharePrice(price, currency as any)}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {marketPrice && (
        <div className="mt-2 text-[0.6875rem] text-[var(--text-tertiary)]">
          Current Price: {formatSharePrice(marketPrice, currency as any)}
        </div>
      )}
    </Card>
  );
};

export default SensitivityHeatmap;
