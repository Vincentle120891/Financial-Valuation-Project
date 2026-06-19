import React, { useState, useEffect, useRef } from 'react';
import api from '../services/api';

/**
 * ApiKeyDebugButton Component
 * 
 * Shows: API key status + real-time process log + edit keys.
 * 
 * Props:
 *   variant: 'inline' | 'floating' (default: 'floating')
 *     - 'inline' renders a compact button suitable for embedding in a sidebar/panel
 *     - 'floating' renders the original fixed-position button
 */
const ApiKeyDebugButton = ({ variant = 'floating' }) => {
  const [isOpen, setIsOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const [backendData, setBackendData] = useState(null);
  const [error, setError] = useState(null);
  const [editMode, setEditMode] = useState(false);
  const [editKeys, setEditKeys] = useState({});
  const [saveStatus, setSaveStatus] = useState(null);
  const [activeTab, setActiveTab] = useState('status'); // 'status' | 'process' | 'edit'
  const [processLogs, setProcessLogs] = useState([]);
  const logEndRef = useRef(null);

  // Listen for process log events from anywhere in the app
  useEffect(() => {
    const handler = (e) => {
      const { step, message, status, details } = e.detail;
      setProcessLogs(prev => [...prev, {
        id: Date.now() + Math.random(),
        timestamp: new Date().toLocaleTimeString(),
        step, message, status, details,
      }]);
    };
    window.addEventListener('api-process-log', handler);
    return () => window.removeEventListener('api-process-log', handler);
  }, []);

  const getStoredKeys = () => ({
    fmp: localStorage.getItem('fmp_api_key') || '',
    alphaVantage: localStorage.getItem('alpha_vantage_api_key') || '',
    rapidapi: localStorage.getItem('rapidapi_av_key') || '',
    fred: localStorage.getItem('fred_api_key') || '',
    openrouter: localStorage.getItem('openrouter_api_key') || '',
    openai: localStorage.getItem('openai_api_key') || '',
    groq: localStorage.getItem('groq_api_key') || '',
    gemini: localStorage.getItem('gemini_api_key') || '',
    qwen: localStorage.getItem('qwen_api_key') || '',
  });

  const addLog = (step, message, status = 'info', details = null) => {
    const entry = {
      id: Date.now() + Math.random(),
      timestamp: new Date().toLocaleTimeString(),
      step,
      message,
      status, // 'info' | 'success' | 'warning' | 'error'
      details,
    };
    setProcessLogs(prev => [...prev, entry]);
  };

  const clearLogs = () => setProcessLogs([]);

  const fetchBackendData = async () => {
    setLoading(true);
    setError(null);
    try {
      addLog('System', 'Fetching backend key status...', 'info');
      const response = await api.get('/debug/api-keys');
      setBackendData(response.data.data);
      addLog('System', 'Backend key status loaded', 'success');
      try {
        const mgrResp = await api.get('/debug/api-key-manager');
        setBackendData(prev => ({ ...prev, key_manager: mgrResp.data }));
        addLog('System', `Key manager: ${mgrResp.data.summary?.total_services || 0} services, ${mgrResp.data.summary?.total_keys_registered || 0} keys`, 'info');
      } catch (_) {
        addLog('System', 'Key manager endpoint not available', 'warning');
      }
    } catch (err) {
      setError(err.message || 'Failed to fetch debug data');
      addLog('System', `Failed to fetch backend data: ${err.message}`, 'error');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => { if (isOpen) { fetchBackendData(); setEditKeys(getStoredKeys()); } }, [isOpen]);
  
  // Recompute storedKeys when editKeys change (after save)
  const storedKeys = getStoredKeys();
  // Merge with editKeys for live preview
  const liveKeys = { ...storedKeys };
  Object.entries(editKeys).forEach(([name, value]) => {
    if (value !== undefined && value !== '') {
      liveKeys[name] = value.split('\n').find(k => k.trim()) || '';
    }
  });

  const maskKey = (key) => {
    if (!key || key.length < 8) return '****';
    return `${key.substring(0, 4)}...${key.substring(key.length - 4)}`;
  };

  const isPlaceholder = (key) => !key || key.includes('your_') || key === '';

  const handleSaveKeys = () => {
    Object.entries(editKeys).forEach(([name, value]) => {
      // For rapidapi, store under rapidapi_av_key (used by AlphaVantageService)
      const storageKey = name === 'rapidapi' ? 'rapidapi_av_key' : `${name}_api_key`;
      if (value.trim()) {
        localStorage.setItem(storageKey, value.trim());
        const keyCount = value.trim().split('\n').filter(k => k.trim()).length;
        addLog('Edit', `Saved ${name}: ${keyCount} key(s)`, 'success');
      } else {
        localStorage.removeItem(storageKey);
        addLog('Edit', `Removed ${name} keys`, 'info');
      }
    });
    setSaveStatus('Saved! Refreshing...');
    setTimeout(() => {
      setSaveStatus(null);
      setActiveTab('status');
      // Force re-read from localStorage
      setEditKeys(getStoredKeys());
      fetchBackendData();
    }, 300);
  };

  const serviceConfig = [
    { key: 'fmp', name: 'FMP', icon: '🔑', headerKey: 'x-api-key-fmp', ls: 'fmp', desc: 'Peer discovery, financial statements' },
    { key: 'alphaVantage', name: 'Alpha Vantage (Direct)', icon: '📊', headerKey: 'x-api-key-alphavantage', ls: 'alphaVantage', desc: 'Direct AV API key (5 req/min)' },
    { key: 'rapidapi', name: 'Alpha Vantage (RapidAPI)', icon: '🚀', headerKey: 'x-api-key-rapidapi', ls: 'rapidapi', desc: 'RapidAPI AV key (500 req/month, multiple keys rotate)' },
    { key: 'fred', name: 'FRED', icon: '🏛️', headerKey: 'x-api-key-fred', ls: 'fred', desc: 'US Treasury yields (Risk-Free Rate)' },
    { key: 'openrouter', name: 'OpenRouter', icon: '🤖', headerKey: 'x-api-key-openrouter', ls: 'openrouter', desc: 'Primary AI provider' },
    { key: 'openai', name: 'OpenAI', icon: '🧠', headerKey: 'x-api-key-openai', ls: 'openai', desc: 'GPT-4o / GPT-4o-mini' },
    { key: 'groq', name: 'Groq', icon: '⚡', headerKey: 'x-api-key-groq', ls: 'groq', desc: 'Fast AI inference' },
    { key: 'gemini', name: 'Gemini', icon: '✨', headerKey: 'x-api-key-gemini', ls: 'gemini', desc: 'AI inference fallback' },
  ];

  const getBackendInfo = (headerKey) => {
    if (!backendData) return { received: null, source: null, headerPresent: false, envPresent: false };
    const svc = headerKey.replace('x-api-key-', '');
    return {
      received: backendData.received_headers?.[headerKey] || null,
      source: backendData.key_sources?.[svc]?.source || null,
      headerPresent: backendData.key_sources?.[svc]?.header_present || false,
      envPresent: backendData.key_sources?.[svc]?.env_present || false,
    };
  };

  const getStatusColor = (configured, working) => {
    if (configured && working) return { bg: '#f0fdf4', border: '#86efac', badge: '#dcfce7', badgeText: '#166534', label: '✓ Active' };
    if (configured) return { bg: '#fffbeb', border: '#fde68a', badge: '#fef3c7', badgeText: '#92400e', label: '⚠ Configured' };
    return { bg: '#fef2f2', border: '#fecaca', badge: '#fee2e2', badgeText: '#991b1b', label: '✗ Missing' };
  };

  const logColorMap = { success: '#16a34a', warning: '#d97706', error: '#dc2626', info: '#6b7280' };

  return (
    <>
      {/* ── Trigger Button ──────────────────────────────────────────────────── */}
      {variant === 'inline' ? (
        <button onClick={() => setIsOpen(true)}
          className="w-full text-left text-[10px] text-slate-400 hover:text-white border border-slate-600 px-2 py-1 rounded transition-colors flex items-center gap-1.5"
          title="API Key Manager">
          🔍 API Keys
          {processLogs.filter(l => l.status === 'error').length > 0 && (
            <span className="w-1.5 h-1.5 bg-red-500 rounded-full animate-pulse ml-auto"></span>
          )}
        </button>
      ) : (
        <button onClick={() => setIsOpen(true)}
          className="fixed top-[60px] right-6 z-[200] inline-flex items-center gap-2 px-4 py-3 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-full shadow-lg hover:shadow-xl transition-all cursor-pointer"
          title="API Key Manager">
          <svg className="w-5 h-5" fill="none" viewBox="0 0 24 24" strokeWidth="2" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
            <path strokeLinecap="round" strokeLinejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
          </svg>
          <span className="hidden sm:inline">🔍 API Keys</span>
          {processLogs.filter(l => l.status === 'error').length > 0 && (
            <span className="w-2 h-2 bg-red-500 rounded-full animate-pulse"></span>
          )}
        </button>
      )}

      {/* ── Modal Dialog ────────────────────────────────────────────────────── */}
      {isOpen && (
        <div className="fixed inset-0 bg-black/50 flex items-start justify-center z-[200] p-2 sm:p-4">
          <div className="bg-white rounded-lg shadow-2xl w-full max-w-5xl flex flex-col" style={{ maxHeight: '92vh' }}>
            {/* Header */}
            <div className="p-4 border-b border-gray-200 flex-shrink-0">
              <div className="flex items-center justify-between">
                <h2 className="text-lg font-bold text-gray-800">API Key Manager</h2>
                <button onClick={() => setIsOpen(false)} className="text-gray-400 hover:text-gray-600 p-1">
                  <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              {/* Tabs */}
              <div className="flex gap-1 mt-3 bg-gray-100 p-1 rounded-lg">
                {[
                  { id: 'status', label: '🔑 Key Status' },
                  { id: 'process', label: `📋 Process Log (${processLogs.length})` },
                  { id: 'edit', label: '✏️ Edit Keys' },
                ].map(tab => (
                  <button key={tab.id} onClick={() => setActiveTab(tab.id)}
                    className={`flex-1 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${activeTab === tab.id ? 'bg-white shadow text-gray-900' : 'text-gray-600 hover:text-gray-900'}`}>
                    {tab.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3">
              {saveStatus && <div className="p-2 bg-green-50 border border-green-200 rounded text-green-800 text-sm">{saveStatus}</div>}
              {error && <div className="p-2 bg-red-50 border border-red-200 rounded text-red-800 text-sm">{error}</div>}

              {/* Tab: Key Status */}
              {activeTab === 'status' && (
                <div className="space-y-3">
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2">
                    {serviceConfig.map(svc => {
                      // Always read fresh from localStorage for accurate count
                      const storageKey = svc.ls === 'rapidapi' ? 'rapidapi_av_key' : `${svc.ls}_api_key`;
                      const rawStored = localStorage.getItem(storageKey) || '';
                      const keyLines = rawStored.split('\n').filter(k => k.trim());
                      const keyCount = keyLines.length;
                      const firstKey = keyLines[0] || '';
                      const bi = getBackendInfo(svc.headerKey);
                      const configured = keyCount > 0;
                      const working = bi.headerPresent || bi.envPresent;
                      const sc = getStatusColor(configured, working);
                      return (
                        <div key={svc.key} className="border rounded-lg p-2.5" style={{ borderColor: sc.border, background: sc.bg }}>
                          <div className="flex items-center justify-between mb-1">
                            <span className="text-sm font-medium">{svc.icon} {svc.name}</span>
                            <span className="text-xs px-1.5 py-0.5 rounded-full" style={{ background: sc.badge, color: sc.badgeText }}>{sc.label}</span>
                          </div>
                          <div className="text-xs text-gray-600 space-y-0.5">
                            <div>📱 {configured ? `${keyCount} key${keyCount > 1 ? 's' : ''} (${maskKey(firstKey)})` : 'Not set'}</div>
                            <div>🖥️ {bi.received ? maskKey(bi.received) : 'Not received'} <span className="text-gray-400">({bi.source || 'none'})</span></div>
                          </div>
                        </div>
                      );
                    })}
                  </div>
                  {backendData?.key_manager && (
                    <div className="border border-purple-200 rounded-lg p-3">
                      <h4 className="text-sm font-semibold text-purple-900 mb-2">🔄 Key Manager</h4>
                      <div className="grid grid-cols-4 gap-2 text-center text-xs mb-2">
                        <div><div className="text-gray-500">Services</div><div className="font-bold text-purple-700">{backendData.key_manager.summary?.total_services || 0}</div></div>
                        <div><div className="text-gray-500">Keys</div><div className="font-bold text-purple-700">{backendData.key_manager.summary?.total_keys_registered || 0}</div></div>
                        <div><div className="text-gray-500">Requests</div><div className="font-bold text-purple-700">{backendData.key_manager.summary?.total_requests_made || 0}</div></div>
                        <div><div className="text-gray-500">Rate Limits</div><div className={`font-bold ${(backendData.key_manager.summary?.total_rate_limit_hits || 0) > 0 ? 'text-red-600' : 'text-green-600'}`}>{backendData.key_manager.summary?.total_rate_limit_hits || 0}</div></div>
                      </div>
                    </div>
                  )}
                </div>
              )}

              {/* Tab: Process Log */}
              {activeTab === 'process' && (
                <div className="space-y-2">
                  <div className="flex justify-between items-center">
                    <span className="text-sm text-gray-500">{processLogs.length} entries</span>
                    <button onClick={clearLogs} className="text-xs text-gray-400 hover:text-gray-600">Clear</button>
                  </div>
                  {processLogs.length === 0 && (
                    <div className="text-center py-8 text-gray-400 text-sm">
                      No process logs yet. Logs appear when you perform API operations.
                    </div>
                  )}
                  <div className="space-y-1 font-mono text-xs">
                    {processLogs.map(log => (
                      <div key={log.id} className="flex gap-2 py-1 border-b border-gray-100">
                        <span className="text-gray-400 flex-shrink-0 w-20">{log.timestamp}</span>
                        <span className="flex-shrink-0 w-16 font-bold" style={{ color: logColorMap[log.status] }}>[{log.step}]</span>
                        <span className="text-gray-700">{log.message}</span>
                      </div>
                    ))}
                  </div>
                  <div ref={logEndRef} />
                </div>
              )}

              {/* Tab: Edit Keys */}
              {activeTab === 'edit' && (
                <div className="space-y-4">
                  <p className="text-sm text-gray-500">
                    Enter API keys below (one per line for multiple keys). They rotate automatically when rate-limited.
                  </p>
                  {serviceConfig.map(svc => {
                    const currentKeys = (editKeys[svc.ls] || '').split('\n').filter(k => k.trim());
                    const keyCount = currentKeys.length;
                    return (
                      <div key={svc.key} className="border border-gray-200 rounded-lg p-3">
                        <div className="flex items-center justify-between mb-2">
                          <label className="text-sm font-medium text-gray-700">{svc.icon} {svc.name}</label>
                          {keyCount > 0 && (
                            <span className="text-xs px-2 py-0.5 rounded-full bg-green-100 text-green-700">
                              {keyCount} key{keyCount > 1 ? 's' : ''} — rotates on failure
                            </span>
                          )}
                        </div>
                        <textarea
                          value={editKeys[svc.ls] || ''}
                          onChange={e => setEditKeys(prev => ({ ...prev, [svc.ls]: e.target.value }))}
                          className="w-full px-3 py-2 border border-gray-300 rounded-lg text-sm font-mono focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 resize-none"
                          rows={Math.max(2, keyCount + 1)}
                          placeholder={`Enter ${svc.name} API key(s), one per line...`}
                        />
                        {keyCount > 1 && (
                          <p className="text-xs text-gray-400 mt-1">
                            ℹ️ Multiple keys will be tried in order. If key #1 hits rate limit, key #2 is used automatically.
                          </p>
                        )}
                      </div>
                    );
                  })}
                  <button onClick={handleSaveKeys}
                    className="w-full py-2.5 bg-indigo-600 hover:bg-indigo-700 text-white font-medium rounded-lg transition-colors">
                    Save All Keys
                  </button>
                </div>
              )}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

// Process log helper - can be called from anywhere in the app
export const logApiProcess = (step, message, status = 'info', details = null) => {
  // Dispatch custom event that ApiKeyDebugButton listens to
  window.dispatchEvent(new CustomEvent('api-process-log', { detail: { step, message, status, details } }));
};

export default ApiKeyDebugButton;
