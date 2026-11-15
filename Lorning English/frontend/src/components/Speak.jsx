import { Volume2 } from 'lucide-react';

const LANGS = { en: 'en-US', uz: 'uz-UZ', ru: 'ru-RU' };

/** Matnni brauzerning ovoz sintezatori (Web Speech API) bilan o'qiydi. */
export function speak(text, lang = 'en') {
  if (!text || typeof window === 'undefined' || !window.speechSynthesis) return false;
  try {
    window.speechSynthesis.cancel();
    const u = new SpeechSynthesisUtterance(text);
    u.lang = LANGS[lang] || lang;
    u.rate = 0.9;
    const voice = window.speechSynthesis.getVoices().find(v => v.lang && v.lang.toLowerCase().startsWith(u.lang.slice(0, 2).toLowerCase()));
    if (voice) u.voice = voice;
    window.speechSynthesis.speak(u);
    return true;
  } catch { return false; }
}

/** Eshitish belgisi: bossa so'zni aytadi */
export default function Speak({ text, lang = 'en', size = 16, className = 'btn btn-ghost btn-icon btn-sm' }) {
  return (
    <button type="button" className={className} aria-label="Listen" title="Listen" disabled={!text}
      onClick={e => { e.stopPropagation(); speak(text, lang); }}>
      <Volume2 size={size} />
    </button>
  );
}
