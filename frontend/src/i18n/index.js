import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import en from './en';
import vi from './vi';

const resources = {
  en: en,
  vi: vi,
};

// Language persistence: read from localStorage, fallback to browser preference
const savedLang = typeof localStorage !== 'undefined'
  ? localStorage.getItem('fv-language')
  : null;

const browserLang = typeof navigator !== 'undefined'
  ? navigator.language.startsWith('vi') ? 'vi' : 'en'
  : 'en';

i18n
  .use(initReactI18next)
  .init({
    resources,
    lng: savedLang || browserLang || 'en',
    fallbackLng: 'en',
    interpolation: {
      escapeValue: false, // React already protects from XSS
    },
  });

// Persist language changes to localStorage
i18n.on('languageChanged', (lng) => {
  try {
    localStorage.setItem('fv-language', lng);
  } catch {
    // localStorage unavailable — silent fail
  }
});

export default i18n;
