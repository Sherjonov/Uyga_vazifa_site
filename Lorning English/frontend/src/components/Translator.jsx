import { useState } from 'react';
import { ArrowLeftRight, Check, Copy, Languages, X } from 'lucide-react';
import { Spinner } from './Loader';
import Speak from './Speak';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';
import '../styles/extra.css';

const NAMES = { en: 'tr.en', uz: 'tr.uz' };

/** Tarjimon: Inglizcha ⇄ O'zbekcha. Backend /translate (hozircha Ustoz AI modeli orqali) */
export default function Translator({ model }) {
  const { t } = useLang();
  const toast = useToast();
  const [src, setSrc] = useState('en');
  const [text, setText] = useState('');
  const [out, setOut] = useState('');
  const [busy, setBusy] = useState(false);
  const [copied, setCopied] = useState(false);
  const target = src === 'en' ? 'uz' : 'en';

  const run = async () => {
    if (!text.trim() || busy) return;
    setBusy(true);
    try {
      const { data } = await api.post('/translate', { text, source: src, target, model: model || null });
      setOut(data.translation);
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  const swap = () => { setSrc(target); if (out) { setText(out); setOut(text); } };
  const copy = async () => {
    try { await navigator.clipboard.writeText(out); setCopied(true); setTimeout(() => setCopied(false), 1500); } catch { toast.error(t('tr.copyFail')); }
  };

  return (
    <div className="tr anim-fade-up">
      <div className="tr-langs">
        <span className="pill">{t(NAMES[src])}</span>
        <button className="btn btn-ghost btn-icon" onClick={swap} aria-label={t('tr.swap')} title={t('tr.swap')}><ArrowLeftRight size={20} /></button>
        <span className="pill">{t(NAMES[target])}</span>
      </div>
      <div className="tr-grid">
        <div style={{ position: 'relative' }}>
          <textarea className="tr-box" value={text} maxLength={3000} placeholder={t('tr.placeholder')}
            onChange={e => setText(e.target.value)} onKeyDown={e => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) run(); }} />
          {text && <button className="btn btn-ghost btn-icon btn-sm" style={{ position: 'absolute', top: 8, right: 8 }} onClick={() => { setText(''); setOut(''); }} aria-label="clear"><X size={15} /></button>}
          {text && <span style={{ position: 'absolute', bottom: 8, right: 8 }}><Speak text={text} lang={src} /></span>}
        </div>
        <div style={{ position: 'relative' }}>
          <div className="tr-box tr-out" aria-live="polite">{out || <span className="muted">{t('tr.result')}</span>}</div>
          {out && <div className="row" style={{ position: 'absolute', bottom: 10, right: 10, gap: 4 }}>
            <Speak text={out} lang={target} />
            <button className="btn btn-ghost btn-sm" onClick={copy}>{copied ? <Check size={15} /> : <Copy size={15} />} {copied ? t('tr.copied') : t('tr.copy')}</button>
          </div>}
        </div>
      </div>
      <div className="row-between"><span className="hint">{text.length}/3000 · Ctrl+Enter</span>
        <button className="btn btn-primary" onClick={run} disabled={busy || !text.trim()}>{busy ? <Spinner size={16} /> : <Languages size={17} />} {t('tr.translate')}</button></div>
    </div>
  );
}
