import React, { useState, useEffect } from 'react';
import { Clock, CheckCircle, Database, ArrowRight, TrendingUp, PieChart, Briefcase, Users, Server } from 'lucide-react';
import { motion } from 'framer-motion';

/**
 * RequirementsStep Component - Step 5: Review Data Requirements BEFORE Retrieval
 *
 * PROFESSIONAL TABLE-BASED UI WITH:
 * - Color-coded categories
 * - Proper "Pending Retrieval" status (NOT "MISSING")
 * - Clean table layout with proper alignment
 * - API source badges
 * - Modern gradient buttons
 */
const RequirementsStep = ({
  selectedModel,
  onBackToModelSelection,
  onRetrieveData,
  loading,
  requiredFields = [],
  calculatedMetrics // Added to track if data was retrieved (parent passes this after successful fetch)
}) => {
  const [localStatus, setLocalStatus] = useState({});

  // FIX: Initialize all fields as 'pending' - they are NOT missing, just not fetched yet!
  useEffect(() => {
    if (requiredFields && requiredFields.length > 0) {
      const initialStatus = {};
      requiredFields.forEach(field => {
        initialStatus[field.id || field.fieldName] = 'pending';
      });
      setLocalStatus(initialStatus);
    }
  }, [requiredFields]);

  // Check if data has already been retrieved - using calculatedMetrics as the indicator
  // The parent component passes calculatedMetrics only after successful data retrieval
  const hasRetrievedData = false; // Always show "Retrieve Data" button - navigation is handled by parent after fetch

  const handleRetrieveData = () => {
    // Set all to fetching state
    const fetchingStatus = { ...localStatus };
    Object.keys(fetchingStatus).forEach(key => {
      fetchingStatus[key] = 'fetching';
    });
    setLocalStatus(fetchingStatus);

    // Trigger actual data fetch - parent handles navigation after success
    if (onRetrieveData) onRetrieveData();
  };

  // Category color mapping with icons
  const getCategoryConfig = (categoryName) => {
    const configMap = {
      'historical_financials': {
        color: 'blue',
        icon: <TrendingUp className="w-5 h-5" />,
        label: 'Historical Financials',
        gradient: 'from-blue-500 to-blue-600'
      },
      'market_data': {
        color: 'purple',
        icon: <PieChart className="w-5 h-5" />,
        label: 'Market Data',
        gradient: 'from-purple-500 to-purple-600'
      },
      'balance_sheet_opening': {
        color: 'teal',
        icon: <Briefcase className="w-5 h-5" />,
        label: 'Balance Sheet (Opening)',
        gradient: 'from-teal-500 to-teal-600'
      },
      'peer_comparables_for_wacc': {
        color: 'indigo',
        icon: <Users className="w-5 h-5" />,
        label: 'Peer Comparables (for WACC)',
        gradient: 'from-indigo-500 to-indigo-600'
      },
      'forecast_drivers': {
        color: 'green',
        icon: <TrendingUp className="w-5 h-5" />,
        label: 'Forecast Drivers',
        gradient: 'from-green-500 to-green-600'
      }
    };
    return configMap[categoryName] || {
      color: 'gray',
      icon: <Database className="w-5 h-5" />,
      label: categoryName,
      gradient: 'from-gray-500 to-gray-600'
    };
  };

  const getColorClasses = (color) => {
    const colors = {
      blue: 'bg-blue-50 border-blue-200 text-blue-900',
      purple: 'bg-purple-50 border-purple-200 text-purple-900',
      teal: 'bg-teal-50 border-teal-200 text-teal-900',
      indigo: 'bg-indigo-50 border-indigo-200 text-indigo-900',
      green: 'bg-green-50 border-green-200 text-green-900',
      gray: 'bg-gray-50 border-gray-200 text-gray-900',
    };
    return colors[color] || colors.gray;
  };

  const getStatusBadge = (fieldId) => {
    const status = localStatus[fieldId] || 'pending';

    if (status === 'fetching') {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-200">
          <Clock className="w-3 h-3 mr-1 animate-spin" />
          Fetching...
        </span>
      );
    }

    if (status === 'retrieved') {
      return (
        <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-green-100 text-green-800 border border-green-200">
          <CheckCircle className="w-3 h-3 mr-1" />
          Retrieved
        </span>
      );
    }

    // CORRECT STATUS: Pending Retrieval (NOT MISSING!)
    return (
      <span className="inline-flex items-center px-3 py-1 rounded-full text-xs font-medium bg-blue-50 text-blue-700 border border-blue-200">
        <Clock className="w-3 h-3 mr-1" />
        Pending Retrieval
      </span>
    );
  };

  const getApiSourceBadge = (fieldName) => {
    const fieldNameLower = fieldName?.toLowerCase() || '';

    if (fieldNameLower.includes('beta') || fieldNameLower.includes('price') || fieldNameLower.includes('market')) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-yellow-100 text-yellow-800 border border-yellow-200">
          <TrendingUp className="w-3 h-3 mr-1" />
          yfinance
        </span>
      );
    }

    if (fieldNameLower.includes('peer')) {
      return (
        <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-green-100 text-green-800 border border-green-200">
          <Users className="w-3 h-3 mr-1" />
          AlphaVantage + yfinance
        </span>
      );
    }

    return (
      <span className="inline-flex items-center px-2.5 py-0.5 rounded-md text-xs font-medium bg-blue-100 text-blue-800 border border-blue-200">
        <Server className="w-3 h-3 mr-1" />
        yfinance
      </span>
    );
  };

  if (!requiredFields || requiredFields.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center p-12 text-gray-500">
        <Clock className="w-16 h-16 mb-4 opacity-50" />
        <p className="text-lg">Loading requirements...</p>
      </div>
    );
  }

  // Group fields by category
  const groupedFields = requiredFields.reduce((groups, field) => {
    const categoryName = field.category || 'Other';
    if (!groups[categoryName]) {
      groups[categoryName] = [];
    }
    groups[categoryName].push(field);
    return groups;
  }, {});

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4 }}
      className="space-y-6"
    >
      {/* Header Section */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <div className="flex items-start justify-between">
          <div>
            <h2 className="text-2xl font-bold text-gray-900 mb-2">Review Required Inputs</h2>
            <p className="text-gray-600 max-w-3xl">
              The following data points are required for your <span className="font-semibold text-blue-600">{selectedModel}</span> analysis.
              None of this data has been fetched yet. Click <span className="font-semibold">"Retrieve Data"</span> below to automatically pull these values from financial APIs.
            </p>
          </div>
          <div className="hidden md:flex items-center justify-center w-16 h-16 rounded-full bg-blue-50 text-blue-600">
            <Database className="w-8 h-8" />
          </div>
        </div>
      </div>

      {/* Info Banner */}
      <div className="bg-blue-50 border-l-4 border-blue-500 p-4 rounded-r-lg">
        <div className="flex items-start">
          <div className="flex-shrink-0">
            <span className="text-2xl">ℹ️</span>
          </div>
          <div className="ml-3">
            <h3 className="text-sm font-medium text-blue-800">About This Step</h3>
            <p className="mt-1 text-sm text-blue-700">
              All fields below show <strong>"Pending Retrieval"</strong> because we haven't fetched data yet.
              This is expected behavior - click the button below to retrieve all data at once.
            </p>
          </div>
        </div>
      </div>

      {/* Requirements Table */}
      <div className="bg-white rounded-xl shadow-sm border border-gray-200 overflow-hidden">
        <div className="overflow-x-auto">
          <table className="w-full">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-1/4">Category & Field</th>
                <th className="px-6 py-4 text-left text-xs font-semibold text-gray-500 uppercase tracking-wider w-1/3">Description</th>
                <th className="px-6 py-4 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider w-1/6">API Source</th>
                <th className="px-6 py-4 text-center text-xs font-semibold text-gray-500 uppercase tracking-wider w-1/6">Status</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {Object.entries(groupedFields).map(([categoryName, fields], catIndex) => {
                const config = getCategoryConfig(categoryName);
                const colorClasses = getColorClasses(config.color);

                return (
                  <React.Fragment key={categoryName}>
                    {/* Category Header Row */}
                    <tr className={`bg-opacity-40 ${colorClasses.split(' ')[0]}`}>
                      <td colSpan="4" className="px-6 py-3">
                        <div className="flex items-center space-x-3">
                          <div className={`p-2 rounded-lg bg-gradient-to-r ${config.gradient} text-white`}>
                            {config.icon}
                          </div>
                          <span className={`font-bold text-sm ${colorClasses.split(' ')[2]}`}>
                            {config.label}
                          </span>
                          <span className="text-xs text-gray-500 font-normal">({fields.length} fields)</span>
                        </div>
                      </td>
                    </tr>

                    {/* Field Rows */}
                    {fields.map((field, fieldIndex) => (
                      <tr key={field.id || fieldIndex} className="hover:bg-gray-50 transition-colors">
                        <td className="px-6 py-4">
                          <div className="flex flex-col">
                            <span className="font-semibold text-gray-900 text-sm">{field.name || field.fieldName}</span>
                            <span className="text-xs text-gray-500 font-mono mt-1">{field.fieldKey || field.fieldName}</span>
                          </div>
                        </td>
                        <td className="px-6 py-4">
                          <p className="text-sm text-gray-600 leading-relaxed">{field.description || 'Required for valuation calculation'}</p>
                        </td>
                        <td className="px-6 py-4 text-center">
                          {getApiSourceBadge(field.fieldName)}
                        </td>
                        <td className="px-6 py-4 text-center">
                          {getStatusBadge(field.id || field.fieldName)}
                        </td>
                      </tr>
                    ))}
                  </React.Fragment>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {/* Action Bar */}
      <div className="flex items-center justify-between pt-4">
        <button
          onClick={onBackToModelSelection}
          disabled={loading}
          className="px-6 py-3 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
        >
          ← Change Model
        </button>

        <div className="flex items-center space-x-4">
          <div className="text-sm text-gray-500 hidden sm:block">
            Ready to fetch <span className="font-bold text-gray-900">{requiredFields.length}</span> data points
          </div>
          <button
            onClick={handleRetrieveData}
            disabled={loading}
            className={`
              flex items-center px-8 py-3 rounded-lg font-bold text-white shadow-lg
              transform transition-all duration-200
              ${loading
                ? 'bg-gray-400 cursor-not-allowed'
                : 'bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-700 hover:to-indigo-700 hover:-translate-y-0.5 hover:shadow-xl'
              }
              focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-blue-500
            `}
          >
            {loading ? (
              <>
                <Clock className="w-5 h-5 mr-2 animate-spin" />
                Retrieving Data...
              </>
            ) : (
              <>
                <Database className="w-5 h-5 mr-2" />
                Retrieve Data
                <ArrowRight className="w-5 h-5 ml-2" />
              </>
            )}
          </button>
        </div>
      </div>
    </motion.div>
  );
};

export default RequirementsStep;