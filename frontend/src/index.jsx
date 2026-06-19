import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import './i18n'; // Initialize i18n before app renders
import ValuationFlow from './components/ValuationFlow.tsx';

const root = ReactDOM.createRoot(document.getElementById('root'));
root.render(
  <React.StrictMode>
    <ValuationFlow />
  </React.StrictMode>
);
