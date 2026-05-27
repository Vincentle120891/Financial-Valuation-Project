import React, { useState, useEffect } from 'react';

const ApiKeyModal = ({ isOpen, onClose, onSave }) => {
  const [apiKeys, setApiKeys] = useState({
    fmp: '',
    fred: '',
    alphaVantage: '',
    secEdgar: ''
  });
  
  const [showPasswords, setShowPasswords] = useState({
    fmp: false,
    fred: false,
    alphaVantage: false,
    secEdgar: false
  });

  const [savedStatus, setSavedStatus] = useState({});

  useEffect(() => {
    if (isOpen) {
      // Load existing keys from localStorage
      const savedKeys = {
        fmp: localStorage.getItem('fmp_api_key') || '',
        fred: localStorage.getItem('fred_api_key') || '',
        alphaVantage: localStorage.getItem('alpha_vantage_api_key') || '',
        secEdgar: localStorage.getItem('sec_edgar_email') || ''
      };
      setApiKeys(savedKeys);
      
      // Check which keys are already set
      const status = {};
      Object.keys(savedKeys).forEach(key => {
        status[key] = savedKeys[key] ? 'configured' : 'missing';
      });
      setSavedStatus(status);
    }
  }, [isOpen]);

  const handleInputChange = (service, value) => {
    setApiKeys(prev => ({
      ...prev,
      [service]: value
    }));
  };

  const handleSave = () => {
    // Save to localStorage
    Object.entries(apiKeys).forEach(([key, value]) => {
      if (value.trim()) {
        localStorage.setItem(`${key}_api_key`, value.trim());
      }
    });
    
    // Update status
    const newStatus = {};
    Object.entries(apiKeys).forEach(([key, value]) => {
      newStatus[key] = value.trim() ? 'configured' : 'missing';
    });
    setSavedStatus(newStatus);

    // Notify parent component
    if (onSave) {
      onSave(apiKeys);
    }

    // Show success message
    setTimeout(() => {
      onClose();
    }, 500);
  };

  const togglePasswordVisibility = (service) => {
    setShowPasswords(prev => ({
      ...prev,
      [service]: !prev[service]
    }));
  };

  if (!isOpen) return null;

  const getServiceConfig = (service) => {
    const configs = {
      fmp: {
        name: 'Financial Modeling Prep (FMP)',
        description: 'Peer discovery, financial statements, and market data',
        link: 'https://financialmodelingprep.com/developer/docs/',
        priority: 'required',
        icon: '🔑'
      },
      alphaVantage: {
        name: 'Alpha Vantage',
        description: 'Additional market data and technical indicators',
        link: 'https://www.alphavantage.co/support/#api-key',
        priority: 'required',
        icon: '📊'
      },
      fred: {
        name: 'FRED API',
        description: 'US Treasury yields (Risk-Free Rate)',
        link: 'https://fred.stlouisfed.org/docs/api/api_key.html',
        priority: 'optional',
        icon: '🏛️'
      },
      secEdgar: {
        name: 'SEC EDGAR Email',
        description: 'SEC filings and company disclosures (format: your-email@domain.com)',
        link: 'https://www.sec.gov/edgar/sec-api-documentation',
        priority: 'optional',
        icon: '📄'
      }
    };
    return configs[service] || {};
  };

  const getServiceDescription = (service) => {
    const config = getServiceConfig(service);
    return config.description || '';
  };

  const getServiceLink = (service) => {
    const config = getServiceConfig(service);
    return config.link || '#';
  };

  const getPriorityBadge = (service) => {
    const config = getServiceConfig(service);
    if (config.priority === 'required') {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-red-100 text-red-800 font-medium">
          REQUIRED
        </span>
      );
    } else {
      return (
        <span className="px-2 py-1 text-xs rounded-full bg-blue-100 text-blue-800 font-medium">
          OPTIONAL
        </span>
      );
    }
  };

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4">
      <div className="bg-white rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto">
        {/* Header */}
        <div className="p-6 border-b border-gray-200">
          <div className="flex justify-between items-center">
            <h2 className="text-2xl font-bold text-gray-800">API Key Configuration</h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-gray-600 transition-colors"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
          <p className="mt-2 text-sm text-gray-600">
            Configure API keys to enable advanced features and real-time data fetching. 
            Keys are stored locally in your browser and sent securely via HTTPS headers.
          </p>
        </div>

        {/* API Key Forms */}
        <div className="p-6 space-y-6">
          {/* Required APIs Section */}
          <div className="space-y-4">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide border-b border-gray-200 pb-2">
              Required APIs (Full Functionality)
            </h3>
            {Object.entries(apiKeys).filter(([service]) => 
              getServiceConfig(service).priority === 'required'
            ).map(([service, value]) => (
              <div key={service} className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-sm font-medium text-gray-700">
                    {getServiceConfig(service).icon} {getServiceConfig(service).name}
                  </label>
                  <div className="flex items-center space-x-2">
                    {getPriorityBadge(service)}
                    {savedStatus[service] && (
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        savedStatus[service] === 'configured' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {savedStatus[service] === 'configured' ? '✓ Configured' : '⚠ Missing'}
                      </span>
                    )}
                  </div>
                </div>
                
                <p className="text-xs text-gray-500">
                  {getServiceDescription(service)}
                  {' '}-{' '}
                  <a 
                    href={getServiceLink(service)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline"
                  >
                    Get API Key
                  </a>
                </p>

                <div className="relative">
                  <input
                    type={showPasswords[service] ? 'text' : 'password'}
                    value={value}
                    onChange={(e) => handleInputChange(service, e.target.value)}
                    placeholder={`Enter your ${service} API key`}
                    className="w-full px-4 py-2 pr-12 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility(service)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPasswords[service] ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>

          {/* Optional APIs Section */}
          <div className="space-y-4 pt-4 border-t border-gray-200">
            <h3 className="text-sm font-semibold text-gray-700 uppercase tracking-wide border-b border-gray-200 pb-2">
              Optional APIs (Enhanced Data)
            </h3>
            {Object.entries(apiKeys).filter(([service]) => 
              getServiceConfig(service).priority === 'optional'
            ).map(([service, value]) => (
              <div key={service} className="space-y-2">
                <div className="flex justify-between items-center">
                  <label className="block text-sm font-medium text-gray-700">
                    {getServiceConfig(service).icon} {getServiceConfig(service).name}
                  </label>
                  <div className="flex items-center space-x-2">
                    {getPriorityBadge(service)}
                    {savedStatus[service] && (
                      <span className={`px-2 py-1 text-xs rounded-full ${
                        savedStatus[service] === 'configured' 
                          ? 'bg-green-100 text-green-800' 
                          : 'bg-yellow-100 text-yellow-800'
                      }`}>
                        {savedStatus[service] === 'configured' ? '✓ Configured' : '⚠ Missing'}
                      </span>
                    )}
                  </div>
                </div>
                
                <p className="text-xs text-gray-500">
                  {getServiceDescription(service)}
                  {' '}-{' '}
                  <a 
                    href={getServiceLink(service)}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="text-blue-600 hover:text-blue-800 underline"
                  >
                    Get API Key
                  </a>
                </p>

                <div className="relative">
                  <input
                    type={showPasswords[service] ? 'text' : 'password'}
                    value={value}
                    onChange={(e) => handleInputChange(service, e.target.value)}
                    placeholder={
                      service === 'secEdgar' 
                        ? 'Enter your email for SEC EDGAR' 
                        : `Enter your ${service} API key`
                    }
                    className="w-full px-4 py-2 pr-12 border border-gray-300 rounded-md focus:ring-2 focus:ring-blue-500 focus:border-blue-500 transition-shadow"
                  />
                  <button
                    type="button"
                    onClick={() => togglePasswordVisibility(service)}
                    className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600"
                  >
                    {showPasswords[service] ? (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                      </svg>
                    ) : (
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                      </svg>
                    )}
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Footer */}
        <div className="p-6 border-t border-gray-200 bg-gray-50 rounded-b-lg">
          <div className="flex justify-between items-center">
            <p className="text-xs text-gray-500">
              🔒 Keys stored locally, sent securely via HTTPS headers
            </p>
            <div className="flex space-x-3">
              <button
                onClick={onClose}
                className="px-4 py-2 text-sm font-medium text-gray-700 bg-white border border-gray-300 rounded-md hover:bg-gray-50 transition-colors"
              >
                Cancel
              </button>
              <button
                onClick={handleSave}
                className="px-4 py-2 text-sm font-medium text-white bg-blue-600 rounded-md hover:bg-blue-700 transition-colors"
              >
                Save Configuration
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};

export default ApiKeyModal;
