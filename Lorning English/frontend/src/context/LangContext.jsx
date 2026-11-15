import { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';
import api, { getToken } from '../api/axios';
import uz from '../i18n/uz';
import en from '../i18n/en';
import ru from '../i18n/ru';

const DICTS = { uz, en, ru };
const LangContext = createContext(null);
export const useLang = () => useContext(LangContext);

export const LANGS = [
  { code: 'uz', flag: '🇺🇿', short: 'UZ', name: "O'zbek" },
  { code: 'en', flag: '🇬🇧', short: 'EN', name: 'English' },
  { code: 'ru', flag: '🇷🇺', short: 'RU', name: 'Русский' }
];

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(() => {
    const s = localStorage.getItem('aedu_lang');
    return DICTS[s] ? s : 'uz';
  });

  useEffect(() => {
    localStorage.setItem('aedu_lang', lang);
    document.documentElement.setAttribute('lang', lang);
  }, [lang]);

  const setLang = useCallback((next, persist = true) => {
    if (!DICTS[next]) return;
    localStorage.setItem('aedu_lang', next); // axios shu qiymatni X-Lang sifatida yuboradi
    setLangState(next);
    if (persist && getToken()) api.put('/settings/preferences', { language: next }).catch(() => {});
  }, []);

  const t = useCallback(
    (key, vars) => {
      let s = DICTS[lang][key] ?? DICTS.uz[key] ?? key;
      if (vars) Object.keys(vars).forEach(k => { s = s.replaceAll(`{${k}}`, vars[k]); });
      return s;
    },
    [lang]
  );

  const value = useMemo(() => ({ lang, setLang, t }), [lang, setLang, t]);
  return <LangContext.Provider value={value}>{children}</LangContext.Provider>;
}
