import { LANGS, useLang } from '../context/LangContext';
import './LangSwitcher.css';

export default function LangSwitcher({ compact = false }) {
  const { lang, setLang } = useLang();
  return (
    <div className={`lang-switch ${compact ? 'compact' : ''}`} role="group" aria-label="language">
      {LANGS.map(l => (
        <button key={l.code} className={l.code === lang ? 'active' : ''} onClick={() => setLang(l.code)} title={l.name}>
          <span className="lang-flag">{l.flag}</span>
          <span className="lang-code">{l.short}</span>
        </button>
      ))}
    </div>
  );
}
