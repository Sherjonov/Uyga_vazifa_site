import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api, { getToken } from '../api/axios';

const ThemeContext = createContext(null);
export const useTheme = () => useContext(ThemeContext);

const initial = () => {
  const saved = localStorage.getItem('aedu_theme');
  if (saved === 'light' || saved === 'dark') return saved;
  return window.matchMedia?.('(prefers-color-scheme: light)').matches ? 'light' : 'dark';
};

export function ThemeProvider({ children }) {
  const [theme, setThemeState] = useState(initial);

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme);
    localStorage.setItem('aedu_theme', theme);
    document.querySelector('meta[name="theme-color"]')?.setAttribute('content', theme === 'dark' ? '#080b1a' : '#f3f4fb');
  }, [theme]);

  const setTheme = useCallback((next, persist = true) => {
    setThemeState(next);
    if (persist && getToken()) api.put('/settings/preferences', { theme: next }).catch(() => {});
  }, []);

  const toggle = useCallback(() => setTheme(theme === 'dark' ? 'light' : 'dark'), [theme, setTheme]);

  return <ThemeContext.Provider value={{ theme, setTheme, toggle }}>{children}</ThemeContext.Provider>;
}
