import React from 'react';
import { useTranslation } from 'react-i18next';

/**
 * TranslationNotice — System no-conversion disclaimer.
 * Fixed at the bottom of the viewport, always visible.
 * 
 * Desktop: positioned right of the 280px sidebar
 * Mobile: full-width, positioned above the 48px bottom nav
 * 
 * Font: Geist Mono (var(--font-mono))
 * Size: 10px
 * Color: var(--text-tertiary) — low contrast, non-intrusive
 */
const TranslationNotice = () => {
  const { t } = useTranslation();
  const notice = t('notices.translation_disclaimer');

  return (
    <div
      className="translation-notice"
      style={{
        position: 'fixed',
        bottom: 0,
        left: 0,
        right: 0,
        zIndex: 40,
        fontFamily: 'var(--font-mono)',
        fontSize: '10px',
        lineHeight: '1.5',
        color: 'var(--text-tertiary)',
        letterSpacing: '0.01em',
        borderTop: '1px solid var(--border-default)',
        background: 'var(--canvas-bg)',
        padding: '4px 16px',
        textAlign: 'center',
      }}
    >
      {notice}
    </div>
  );
};

export default TranslationNotice;
