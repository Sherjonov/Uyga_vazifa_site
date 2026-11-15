import { useCallback, useEffect, useRef, useState } from 'react';
import { Check, ChevronLeft, ChevronRight, Image as ImageIcon, LayoutTemplate, Maximize2, Minimize2, X } from 'lucide-react';
import { useLang } from '../context/LangContext';
import './SlideDeck.css';

const TOKEN = /("[^"\n]*"|'[^'\n]*'|#.*$|\b(?:def|class|if|elif|else|for|while|in|return|import|from|as|match|case|try|except|finally|with|lambda|print|input|True|False|None|and|or|not|break|continue|pass)\b|\b\d+(?:\.\d+)?\b)/gm;

function Highlight({ code }) {
  const parts = [];
  let last = 0;
  for (const m of code.matchAll(TOKEN)) {
    if (m.index > last) parts.push(code.slice(last, m.index));
    const tok = m[0];
    const cls = /^["']/.test(tok) ? 'str' : tok[0] === '#' ? 'com' : /^\d/.test(tok) ? 'num' : 'kw';
    parts.push(<span key={m.index} className={`tk-${cls}`}>{tok}</span>);
    last = m.index + tok.length;
  }
  if (last < code.length) parts.push(code.slice(last));
  return <>{parts}</>;
}

const splitItem = s => {
  const m = s.match(/^(.{2,32}?)\s(?:—|–|-|:)\s+(.+)$/) || s.match(/^(.{2,32}?):\s*(.+)$/);
  return m ? { title: m[1], desc: m[2] } : null;
};

function Bullets({ items }) {
  const parts = items.map(splitItem);
  if (items.length >= 2 && items.length <= 6 && parts.every(Boolean)) {
    return (
      <div className="deck-cards">
        {parts.map((p, i) => <div key={i} className="deck-card"><span className="deck-card-n">{i + 1}</span><strong>{p.title}</strong><span>{p.desc}</span></div>)}
      </div>
    );
  }
  return <ul className="deck-list">{items.map((it, i) => <li key={i}>{it}</li>)}</ul>;
}

function Quiz({ questions, picks, onPick }) {
  const { t } = useLang();
  const [qi, setQi] = useState(0);
  const q = questions[qi];
  const pick = picks?.[qi];
  const known = q.correct_index != null;
  return (
    <div className="deck-quiz">
      <div className="quiz-head">
        <span className="quiz-count">⚡ {t('deck.question')} {qi + 1} / {questions.length}</span>
        {questions.length > 1 && <div className="quiz-pills">{questions.map((_, i) => <button key={i} className={`quiz-pill ${i === qi ? 'cur' : ''} ${picks?.[i] != null ? 'done' : ''}`} onClick={() => setQi(i)}>{i + 1}</button>)}</div>}
      </div>
      <div className="quiz-card">
        <div className="quiz-q">❓ {q.text}</div>
        {q.code && <pre className="deck-code"><Highlight code={q.code} /></pre>}
        <div className="quiz-opts">
          {q.options.map((o, i) => {
            let cls = '';
            if (pick != null && known) cls = i === q.correct_index ? 'right' : pick === i ? 'wrong' : '';
            else if (pick === i) cls = 'picked';
            return (
              <button key={i} className={`quiz-opt ${cls}`} onClick={() => onPick(qi, i)}>
                <span className="quiz-l">{String.fromCharCode(65 + i)}</span><span className="spacer">{o}</span>
                {cls === 'right' && <Check size={18} />}{cls === 'wrong' && <X size={18} />}
              </button>
            );
          })}
        </div>
        {pick != null && known && <div className={`quiz-note ${pick === q.correct_index ? 'ok' : 'bad'}`}>{pick === q.correct_index ? t('deck.right') : t('deck.wrong', { a: String.fromCharCode(65 + q.correct_index) })}</div>}
      </div>
    </div>
  );
}

/** slides: [{page, url, content}] — content bo'lsa chiroyli slayd, bo'lmasa PDF sahifa rasmi */
export default function SlideDeck({ slides = [], title }) {
  const { t } = useLang();
  const [i, setI] = useState(0);
  const [raw, setRaw] = useState(false);
  const [full, setFull] = useState(false);
  const [picks, setPicks] = useState({});
  const box = useRef(null);
  const touch = useRef(null);
  const n = slides.length;
  const go = useCallback(d => setI(x => Math.min(n - 1, Math.max(0, x + d))), [n]);

  useEffect(() => {
    const onKey = e => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
      if (e.key === 'ArrowRight' || e.key === ' ') { e.preventDefault(); go(1); }
      if (e.key === 'ArrowLeft') go(-1);
      if (e.key === 'f' || e.key === 'F') (document.fullscreenElement ? document.exitFullscreen() : box.current?.requestFullscreen?.());
    };
    const onFs = () => setFull(document.fullscreenElement === box.current);
    window.addEventListener('keydown', onKey);
    document.addEventListener('fullscreenchange', onFs);
    return () => { window.removeEventListener('keydown', onKey); document.removeEventListener('fullscreenchange', onFs); };
  }, [go]);

  if (!n) return null;
  const s = slides[i];
  const c = s.content;
  const showImage = raw || !c;
  const onStage = e => { if (!e.target.closest('button, a, pre, .quiz-card, img, .deck-card')) go(1); };
  const onPick = (qi, oi) => setPicks(p => ({ ...p, [i]: { ...(p[i] || {}), [qi]: oi } }));

  return (
    <div className={`deck ${full ? 'is-full' : ''}`} ref={box}>
      <div className="deck-top">
        <div><strong>{title}</strong><span>{t('deck.slide')} {i + 1} / {n}</span></div>
        <div className="row" style={{ gap: 8 }}>
          {c && <button className="btn btn-ghost btn-sm" onClick={() => setRaw(r => !r)}>{raw ? <LayoutTemplate size={15} /> : <ImageIcon size={15} />} {raw ? t('deck.designed') : t('deck.original')}</button>}
          <button className="btn btn-ghost btn-icon btn-sm" onClick={() => (document.fullscreenElement ? document.exitFullscreen() : box.current?.requestFullscreen?.())} aria-label="fullscreen">{full ? <Minimize2 size={16} /> : <Maximize2 size={16} />}</button>
        </div>
      </div>
      <div className="deck-stage" onClick={onStage} onTouchStart={e => (touch.current = e.touches[0].clientX)}
        onTouchEnd={e => { if (touch.current != null) { const dx = e.changedTouches[0].clientX - touch.current; if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1); touch.current = null; } }}>
        {showImage ? <img key={s.url} className="deck-img" src={s.url} alt={`${i + 1}`} draggable={false} /> : (
          <div className="deck-slide" key={i}>
            {c.title && <h2 className="deck-title">{c.title}</h2>}
            {c.blocks.map((b, k) => b.type === 'heading' ? <h3 key={k} className="deck-h">{b.text}</h3>
              : b.type === 'para' ? <p key={k} className="deck-p">{b.text}</p>
              : b.type === 'code' ? <pre key={k} className="deck-code"><Highlight code={b.text} /></pre>
              : <Bullets key={k} items={b.items} />)}
            {c.images?.length > 0 && <div className="deck-images">{c.images.map(u => <img key={u} src={u} alt="" loading="lazy" />)}</div>}
            {c.quiz && <Quiz key={i} questions={c.quiz} picks={picks[i]} onPick={onPick} />}
          </div>
        )}
      </div>
      <div className="deck-bar">
        <button className="btn btn-ghost" onClick={() => go(-1)} disabled={i === 0}><ChevronLeft size={17} /> {t('deck.prev')}</button>
        <div className="progress deck-progress"><span style={{ width: `${((i + 1) / n) * 100}%` }} /></div>
        <button className="btn btn-primary" onClick={() => go(1)} disabled={i === n - 1}>{t('deck.next')} <ChevronRight size={17} /></button>
      </div>
      <p className="deck-hint">{t('deck.hint')}</p>
    </div>
  );
}
