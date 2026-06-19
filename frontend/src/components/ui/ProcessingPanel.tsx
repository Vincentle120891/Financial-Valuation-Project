import React, { useState, useEffect, useRef } from 'react';

interface ProcessingPanelProps {
  isProcessing: boolean;
  title?: string;
  logEntries?: string[];
  children: React.ReactNode;
}

/**
 * ProcessingPanel — Advanced Latency Recovery & Visual Shifting Matrix.
 * 
 * When isProcessing=true:
 * - Applies Contrast Lock surface override (theme-specific processing colors)
 * - Renders scanning border animation (40px accent segment travels perimeter in 2s)
 * - Displays monospaced micro-log stream (Geist Mono 11px, line-height 1.2)
 * - Text opacity is NEVER animated — only the border perimeter
 * 
 * When isProcessing=false:
 * - Renders children normally with standard theme tokens
 */
const ProcessingPanel: React.FC<ProcessingPanelProps> = ({
  isProcessing,
  title = 'PROCESSING...',
  logEntries = [],
  children,
}) => {
  const [elapsed, setElapsed] = useState(0);
  const [ellipsis, setEllipsis] = useState('');
  const logRef = useRef<HTMLDivElement>(null);

  // Real-time elapsed timer
  useEffect(() => {
    if (!isProcessing) {
      setElapsed(0);
      return;
    }
    const id = setInterval(() => setElapsed((s) => s + 1), 1000);
    return () => clearInterval(id);
  }, [isProcessing]);

  // Cycling ellipsis
  useEffect(() => {
    if (!isProcessing) return;
    let count = 0;
    const id = setInterval(() => {
      count = (count + 1) % 4;
      setEllipsis(' . '.repeat(count + 1));
    }, 500);
    return () => clearInterval(id);
  }, [isProcessing]);

  // Auto-scroll log to bottom
  useEffect(() => {
    if (logRef.current) {
      logRef.current.scrollTop = logRef.current.scrollHeight;
    }
  }, [logEntries]);

  if (!isProcessing) {
    return <>{children}</>;
  }

  const formatElapsed = (sec: number) => {
    const m = Math.floor(sec / 60);
    const s = sec % 60;
    return `${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}`;
  };

  return (
    <div className="processing-panel" style={{ borderRadius: 'var(--radius-md)', overflow: 'hidden' }}>
      {/* Processing Header */}
      <div
        style={{
          padding: '8px 12px',
          borderBottom: '1px solid var(--processing-border)',
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          fontFamily: 'var(--font-mono)',
          fontSize: '10px',
          letterSpacing: '0.05em',
        }}
      >
        <span>{title}</span>
        <span style={{ opacity: 0.7 }}>[ {formatElapsed(elapsed)} ]</span>
      </div>

      {/* Children (dimmed via Contrast Lock) */}
      <div style={{ opacity: 0.5, pointerEvents: 'none' }}>
        {children}
      </div>

      {/* Micro-log Stream */}
      {logEntries.length > 0 && (
        <div
          ref={logRef}
          className="processing-log"
          style={{
            borderTop: '1px solid var(--processing-border)',
            padding: '6px 12px',
            maxHeight: '120px',
            overflowY: 'auto',
          }}
        >
          {logEntries.map((entry, i) => (
            <div key={i} className="processing-log-line">
              {entry}
            </div>
          ))}
          <div className="processing-log-line">
            {'>'} Scanning{ellipsis}
          </div>
        </div>
      )}
    </div>
  );
};

export default ProcessingPanel;
