import React from 'react';

interface DataFieldDisplayProps {
  label: string;
  dataField?: {
    value: any;
    unit?: string;
    status?: 'fetched' | 'calculated' | 'estimated' | 'missing';
    source?: string;
    confidence?: number;
    periods?: any[];
  };
  className?: string;
}

export const DataFieldDisplay: React.FC<DataFieldDisplayProps> = ({
  label,
  dataField,
  className = '',
}) => {
  if (!dataField) {
    return (
      <div className={`flex items-center justify-between p-3 border rounded-lg bg-muted/20 ${className}`}>
        <span className="text-sm font-medium text-muted-foreground">{label}</span>
        <span className="text-sm text-muted-foreground">No Data</span>
      </div>
    );
  }

  const { value, unit, status, source, confidence, periods } = dataField;

  // Determine status color and icon
  const getStatusConfig = () => {
    switch (status) {
      case 'fetched':
        return { color: 'bg-green-500/10 text-green-700 border-green-200', label: 'Fetched', indicator: '📥' };
      case 'calculated':
        return { color: 'bg-blue-500/10 text-blue-700 border-blue-200', label: 'Calculated', indicator: '📊' };
      case 'estimated':
        return { color: 'bg-yellow-500/10 text-yellow-700 border-yellow-200', label: 'Estimated', indicator: '📝' };
      case 'missing':
        return { color: 'bg-red-500/10 text-red-700 border-red-200', label: 'Missing', indicator: '⚠️' };
      default:
        return { color: 'bg-gray-500/10 text-gray-700 border-gray-200', label: 'Available', indicator: '✓' };
    }
  };

  const statusConfig = getStatusConfig();

  // Format value for display
  const formatValue = (val: any) => {
    if (val === null || val === undefined) return 'N/A';
    if (typeof val === 'number') {
      return new Intl.NumberFormat('en-US', {
        minimumFractionDigits: 0,
        maximumFractionDigits: 2,
      }).format(val);
    }
    return String(val);
  };

  return (
    <div className={`flex flex-col gap-2 p-3 border rounded-lg bg-card hover:bg-accent/5 transition-colors ${className}`}>
      <div className="flex items-center justify-between">
        <span className="text-sm font-medium text-foreground">{label}</span>
        {status && (
          <span className={`px-2 py-1 rounded text-xs font-medium border ${statusConfig.color}`}>
            {statusConfig.indicator} {statusConfig.label}
          </span>
        )}
      </div>

      <div className="flex items-baseline gap-1">
        <span className="text-lg font-semibold text-primary">{formatValue(value)}</span>
        {unit && <span className="text-xs text-muted-foreground">{unit}</span>}
      </div>

      {periods && periods.length > 0 && (
        <div className="mt-2 pt-2 border-t border-border">
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 gap-2">
            {periods.map((period, idx) => (
              <div key={idx} className="text-xs">
                <div className="text-muted-foreground">{period.period}</div>
                <div className="font-medium">{formatValue(period.value)}</div>
              </div>
            ))}
          </div>
        </div>
      )}

      {source && (
        <div className="text-xs text-muted-foreground flex items-center gap-1">
          <span>📥</span>
          Source: {source}
        </div>
      )}

      {confidence !== undefined && (
        <div className="text-xs text-muted-foreground">
          Confidence: {(confidence * 100).toFixed(0)}%
        </div>
      )}
    </div>
  );
};
