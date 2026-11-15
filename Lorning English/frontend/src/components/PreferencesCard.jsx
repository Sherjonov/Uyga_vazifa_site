import { Moon, Sun } from 'lucide-react';
import { LANGS, useLang } from '../context/LangContext';
import { useTheme } from '../context/ThemeContext';

export default function PreferencesCard() {
  const { lang, setLang, t } = useLang();
  const { theme, setTheme } = useTheme();
  return (
    <div className="card">
      <div className="card-title"><h3>{t('settings.language')}</h3></div>
      <div className="row" style={{ marginBottom: 22 }}>
        {LANGS.map(l => (
          <button key={l.code} className={`btn ${lang === l.code ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setLang(l.code)}>{l.flag} {l.name}</button>
        ))}
      </div>
      <div className="card-title"><h3>{t('settings.theme')}</h3></div>
      <div className="row">
        <button className={`btn ${theme === 'light' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTheme('light')}><Sun size={17} /> {t('settings.light')}</button>
        <button className={`btn ${theme === 'dark' ? 'btn-primary' : 'btn-ghost'}`} onClick={() => setTheme('dark')}><Moon size={17} /> {t('settings.dark')}</button>
      </div>
    </div>
  );
}
