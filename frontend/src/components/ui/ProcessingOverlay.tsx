import React, { useState, useEffect, useRef } from 'react';

interface ProcessingOverlayProps {
  isOpen: boolean;
  title?: string;
  subtitle?: string;
  messages?: string[];
  messageInterval?: number;
  accentColor?: string;
}

/**
 * ProcessingOverlay — Bloomberg Terminal "Infinite Execution Engine".
 * 
 * When API processing times are unpredictable, we never render percentage bars,
 * countdown clocks, or frozen states. Instead:
 * - Real-time elapsed timer with milliseconds
 * - Dynamic record counter
 * - Infinite marquee tracker (never stalls, never anchors to completion)
 * - System activity log with cycling ellipsis for waiting states
 * 
 * Font: Geist Mono at 11px
 * Borders: 1px solid var(--border-default)
 * Zero animations except the infinite marquee
 */
const ProcessingOverlay: React.FC<ProcessingOverlayProps> = ({
  isOpen,
  title = 'COMPREHENSIVE MARKET SYSTEM SCANNER',
  subtitle = 'PROCESSING DATA MATRIX COHORTS...',
  messages = [],
  messageInterval = 2500,
}) => {
  const [elapsedMs, setElapsedMs] = useState(0);
  const [msgIdx, setMsgIdx] = useState(0);
  const [logLines, setLogLines] = useState<{ time: string; tag: string; text: string; status: 'DONE' | 'RUNNING' | 'WAITING' }[]>([]);
  const [recordCount, setRecordCount] = useState(0);
  const [ellipsis, setEllipsis] = useState('');
  const marqueeRef = useRef<HTMLDivElement>(null);
  const animFrameRef = useRef<number>(0);
  const startTimeRef = useRef(Date.now());

  // Real-time elapsed timer with milliseconds
  useEffect(() => {
    if (!isOpen) {
      setElapsedMs(0);
      setRecordCount(0);
      setLogLines([]);
      setEllipsis('');
      startTimeRef.current = Date.now();
      return;
    }
    const tick = () => {
      setElapsedMs(Date.now() - startTimeRef.current);
      animFrameRef.current = requestAnimationFrame(tick);
    };
    animFrameRef.current = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(animFrameRef.current);
  }, [isOpen]);

  // Dynamic record counter — increments steadily
  useEffect(() => {
    if (!isOpen) return;
    const id = setInterval(() => {
      setRecordCount((c) => c + Math.floor(Math.random() * 47) + 12);
    }, 200);
    return () => clearInterval(id);
  }, [isOpen]);

  // Cycling ellipsis for waiting states
  useEffect(() => {
    if (!isOpen) return;
    let count = 0;
    const id = setInterval(() => {
      count = (count + 1) % 4;
      setEllipsis(' . '.repeat(count + 1));
    }, 500);
    return () => clearInterval(id);
  }, [isOpen]);

  // Message rotation with log line injection
  useEffect(() => {
    if (!isOpen || messages.length === 0) return;
    const id = setInterval(() => {
      setMsgIdx((i) => {
        const next = (i + 1) % messages.length;
        const now = new Date();
        const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
        setLogLines((prev) => {
          const updated = prev.map((l) => l.status === 'RUNNING' ? { ...l, status: 'DONE' as const } : l);
          const tags = ['SYS_OK', 'STAGE_02', 'MATRIX', 'CORE', 'PIPE', 'SYNC', 'SCAN', 'EVAL'];
          const tag = tags[next % tags.length];
          return [...updated, { time, tag, text: messages[next], status: 'RUNNING' as const }].slice(-10);
        });
        return next;
      });
    }, messageInterval);
    return () => clearInterval(id);
  }, [isOpen, messages.length, messageInterval]);

  // Initialize first log line
  useEffect(() => {
    if (isOpen && messages.length > 0 && logLines.length === 0) {
      const now = new Date();
      const time = `${String(now.getHours()).padStart(2, '0')}:${String(now.getMinutes()).padStart(2, '0')}:${String(now.getSeconds()).padStart(2, '0')}`;
      setLogLines([{ time, tag: 'SYS_OK', text: messages[0], status: 'RUNNING' }]);
    }
  }, [isOpen, messages.length]);

  if (!isOpen) return null;

  // Format elapsed as [ HH:MM:SS.ms ]
  const formatElapsed = (ms: number) => {
    const totalSec = ms / 1000;
    const h = Math.floor(totalSec / 3600);
    const m = Math.floor((totalSec % 3600) / 60);
    const s = Math.floor(totalSec % 60);
    const cs = Math.floor((ms % 1000) / 10);
    return `${String(h).padStart(2, '0')}:${String(m).padStart(2, '0')}:${String(s).padStart(2, '0')}.${String(cs).padStart(2, '0')}`;
  };

  const formatRecordCount = (n: number) => n.toLocaleString();

  const currentMessage = messages.length > 0 ? messages[msgIdx % messages.length] : subtitle;

  return (
    <div
      className="fixed inset-0 flex items-center justify-center"
      style={{ zIndex: 9999, background: 'rgba(8, 12, 20, 0.94)' }}
    >
      <div
        className="w-full max-w-2xl mx-4"
        style={{
          background: 'var(--canvas-surface)',
          border: '1px solid var(--border-default)',
          borderRadius: 'var(--radius-md)',
          fontFamily: 'var(--font-mono)',
          fontSize: '11px',
          lineHeight: '1.6',
          color: 'var(--text-primary)',
          overflow: 'hidden',
        }}
      >
        {/* Terminal Header */}
        <div
          className="px-4 py-2"
          style={{
            background: 'var(--canvas-surface-elevated)',
            borderBottom: '1px solid var(--border-default)',
            display: 'flex',
            justifyContent: 'space-between',
            alignItems: 'center',
          }}
        >
          <span style={{ color: 'var(--text-secondary)', fontSize: '10px', fontWeight: 600, letterSpacing: '0.05em' }}>
            ◆ {title}: MODEL_RUN_ACTIVE
          </span>
        </div>

        {/* Terminal Body */}
        <div className="px-4 py-3">
          {/* Metrics Row */}
          <div className="mb-2" style={{ display: 'flex', gap: '16px', flexWrap: 'wrap' }}>
            <span>
              <span style={{ color: 'var(--text-tertiary)' }}>ELAPSED: </span>
              <span style={{ color: 'var(--text-primary)' }}>[ {formatElapsed(elapsedMs)} ]</span>
            </span>
            <span>
              <span style={{ color: 'var(--text-tertiary)' }}>RECORDS: </span>
              <span style={{ color: 'var(--accent-primary)' }}>[ {formatRecordCount(recordCount)} ]</span>
            </span>
          </div>

          {/* Status Line */}
          <div className="mb-3" style={{ color: 'var(--text-secondary)' }}>
            <span style={{ color: 'var(--text-tertiary)' }}>STATUS: </span>
            {subtitle}
          </div>

          {/* Infinite Marquee Tracker */}
          <div
            className="mb-3"
            style={{
              border: '1px solid var(--border-default)',
              borderRadius: 'var(--radius-sm)',
              padding: '6px 8px',
              overflow: 'hidden',
              position: 'relative',
              background: 'var(--canvas-bg)',
            }}
          >
            <div
              ref={marqueeRef}
              style={{
                display: 'flex',
                whiteSpace: 'nowrap',
                animation: 'infinite-marquee 1.5s linear infinite',
              }}
            >
              <span style={{ color: 'var(--accent-primary)' }}>
                {'█'.repeat(8)}{' '}{`INFINITE TICK TRACKER`}{' '}{'█'.repeat(8)}{'  '}{`INFINITE TICK TRACKER`}{`  `}{`█`.repeat(8)}
              </span>
            </div>
          </div>

          {/* System Activity Log */}
          <div
            className="mb-3"
            style={{
              borderTop: '1px solid var(--border-default)',
              borderBottom: '1px solid var(--border-default)',
              padding: '8px 0',
              maxHeight: '160px',
              overflow: 'hidden',
            }}
          >
            {logLines.map((line, i) => (
              <div key={i} className="mb-0.5" style={{ color: 'var(--text-secondary)' }}>
                <span style={{ color: 'var(--text-tertiary)' }}>{'>'}</span>{' '}
                <span style={{
                  color: line.status === 'DONE' ? 'var(--color-bullish)' : line.status === 'RUNNING' ? 'var(--accent-primary)' : 'var(--text-tertiary)',
                }}>[{line.tag}]</span>{' '}
                <span>{line.text}</span>{' '}
                {line.status === 'DONE' && (
                  <span style={{ color: 'var(--color-bullish)', fontWeight: 600 }}>DONE</span>
                )}
                {line.status === 'RUNNING' && (
                  <span style={{ color: 'var(--accent-primary)', fontWeight: 600 }}>RUNNING</span>
                )}
                {line.status === 'WAITING' && (
                  <span style={{ color: 'var(--color-neutral)' }}>WAITING{ellipsis}</span>
                )}
              </div>
            ))}
          </div>

          {/* Active Thread */}
          <div style={{ color: 'var(--accent-primary)' }}>
            <span style={{ color: 'var(--text-tertiary)' }}>{'>'}</span>{' '}
            {currentMessage}
          </div>
        </div>
      </div>

      {/* Infinite Marquee CSS Animation */}
      <style>{`
        @keyframes infinite-marquee {
          0% { transform: translateX(0); }
          100% { transform: translateX(-33.333%); }
        }
      `}</style>
    </div>
  );
};

export default ProcessingOverlay;
