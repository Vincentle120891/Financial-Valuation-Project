import React from 'react';
import { useTranslation } from 'react-i18next';

/**
 * LanguageToggle — EN ↔ VI language toggle button.
 * Renders a compact globe icon in the app header.
 * Saves language preference to localStorage via i18n.
 * 
 * Translation Mask: Only UI wrappers are toggled.
 * Financial data, acronyms, and calculation states remain English.
 */
const LanguageToggle = () => {
  const { i18n, t } = useTranslation();
  const isVi = i18n.language === 'vi';

  const toggleLanguage = () => {
    i18n.changeLanguage(isVi ? 'en' : 'vi');
  };

  return (
    <button
      onClick={toggleLanguage}
      className="inline-flex items-center justify-center h-7 px-2 rounded
        bg-[var(--border-subtle)] hover:bg-[var(--border-default)]
        text-[var(--text-secondary)] hover:text-[var(--text-primary)]
        cursor-pointer border border-[var(--border-default)]"
      style={{
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        fontWeight: 600,
        letterSpacing: '0.03em',
      }}
      title={isVi ? 'Switch to English' : 'Chuyển sang Tiếng Việt'}
      aria-label={isVi ? 'Switch to English' : 'Chuyển sang Tiếng Việt'}
    >
      {/* Globe icon */}
      <svg
        xmlns="http://www.w3.org/2000/svg"
        width="14"
        height="14"
        viewBox="0 0 24 24"
        fill="none"
        stroke="currentColor"
        strokeWidth="2"
        strokeLinecap="round"
        strokeLinejoin="round"
        className="mr-1"
      >
        <circle cx="12" cy="12" r="10" />
        <path d="M2 12h20" />
        <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z" />
      </svg>
      {isVi ? 'EN' : 'VI'}
    </button>
  );
};

export default LanguageToggle;
