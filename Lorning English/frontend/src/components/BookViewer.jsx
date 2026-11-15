import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Maximize2, Minimize2, Search, ZoomIn, ZoomOut, X } from 'lucide-react';
import * as pdfjs from 'pdfjs-dist';
import workerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';
import { useLang } from '../context/LangContext';
import { Spinner } from './Loader';
import '../styles/extra.css';

pdfjs.GlobalWorkerOptions.workerSrc = workerUrl;

/** PDF kitob ko'ruvchi: qidiruv, sahifaga o'tish, kattalashtirish, full screen (PDF.js) */
export default function BookViewer({ url, title, onClose }) {
  const { t } = useLang();
  const [pdf, setPdf] = useState(null);
  const [page, setPage] = useState(1);
  const [pageInput, setPageInput] = useState('1');
  const [scale, setScale] = useState(1.2);
  const [error, setError] = useState('');
  const [query, setQuery] = useState('');
  const [hits, setHits] = useState(null);
  const [hitIdx, setHitIdx] = useState(0);
  const [searching, setSearching] = useState(false);
  const [full, setFull] = useState(false);
  const canvas = useRef(null);
  const box = useRef(null);
  const textCache = useRef({});
  const total = pdf?.numPages || 0;

  useEffect(() => {
    let alive = true;
    const task = pdfjs.getDocument({ url });
    task.promise.then(doc => { if (alive) setPdf(doc); }).catch(() => alive && setError(t('book.loadError')));
    return () => { alive = false; task.destroy(); };
  }, [url]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (!pdf) return undefined;
    let cancelled = false; let renderTask;
    pdf.getPage(page).then(p => {
      if (cancelled) return;
      const dpr = window.devicePixelRatio || 1;
      const vp = p.getViewport({ scale: scale * dpr });
      const c = canvas.current; if (!c) return;
      c.width = vp.width; c.height = vp.height;
      c.style.width = `${vp.width / dpr}px`; c.style.height = `${vp.height / dpr}px`;
      renderTask = p.render({ canvasContext: c.getContext('2d'), viewport: vp });
      renderTask.promise.catch(() => {});
    });
    setPageInput(String(page));
    return () => { cancelled = true; renderTask?.cancel(); };
  }, [pdf, page, scale]);

  const go = useCallback(n => setPage(p => Math.min(total || 1, Math.max(1, typeof n === 'function' ? n(p) : n))), [total]);

  useEffect(() => {
    const onKey = e => {
      if (['INPUT', 'TEXTAREA'].includes(document.activeElement?.tagName)) return;
      if (e.key === 'ArrowRight' || e.key === 'PageDown') go(p => p + 1);
      if (e.key === 'ArrowLeft' || e.key === 'PageUp') go(p => p - 1);
    };
    window.addEventListener('keydown', onKey);
    const onFs = () => setFull(document.fullscreenElement === box.current);
    document.addEventListener('fullscreenchange', onFs);
    return () => { window.removeEventListener('keydown', onKey); document.removeEventListener('fullscreenchange', onFs); };
  }, [go]);

  const pageText = async n => {
    if (textCache.current[n] == null) {
      const p = await pdf.getPage(n);
      const c = await p.getTextContent();
      textCache.current[n] = c.items.map(i => i.str).join(' ').replace(/\s+/g, ' ');
    }
    return textCache.current[n];
  };

  const search = async e => {
    e?.preventDefault();
    const q = query.trim().toLowerCase();
    if (!q || !pdf) return setHits(null);
    setSearching(true);
    const found = [];
    for (let n = 1; n <= pdf.numPages; n += 1) {
      const text = await pageText(n);
      const at = text.toLowerCase().indexOf(q);
      if (at >= 0) found.push({ page: n, snippet: text.slice(Math.max(0, at - 30), at + q.length + 50) });
      if (found.length >= 200) break;
    }
    setHits(found); setHitIdx(0); setSearching(false);
    if (found[0]) go(found[0].page);
  };
  const jumpHit = d => { if (!hits?.length) return; const i = (hitIdx + d + hits.length) % hits.length; setHitIdx(i); go(hits[i].page); };
  const submitPage = e => { e.preventDefault(); const n = parseInt(pageInput, 10); if (n) go(n); else setPageInput(String(page)); };
  const toggleFull = () => { if (document.fullscreenElement) document.exitFullscreen(); else box.current?.requestFullscreen?.(); };

  return (
    <div className="pdfv" ref={box}>
      <div className="pdfv-bar">
        {title && <strong style={{ marginRight: 6, maxWidth: 220, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>{title}</strong>}
        <button onClick={() => go(p => p - 1)} disabled={page <= 1} aria-label="prev"><ChevronLeft size={18} /></button>
        <form onSubmit={submitPage} style={{ display: 'flex', alignItems: 'center', gap: 6 }}>
          <input className="input pg" value={pageInput} onChange={e => setPageInput(e.target.value.replace(/\D/g, ''))} aria-label={t('book.goto')} />
          <span>/ {total || '–'}</span>
        </form>
        <button onClick={() => go(p => p + 1)} disabled={page >= total} aria-label="next"><ChevronRight size={18} /></button>
        <form onSubmit={search} style={{ display: 'flex', gap: 6 }}>
          <input className="input q" value={query} onChange={e => setQuery(e.target.value)} placeholder={t('book.search')} />
          <button type="submit" aria-label="search">{searching ? <Spinner size={16} /> : <Search size={16} />}</button>
        </form>
        {hits && <><span>{hits.length ? `${hitIdx + 1}/${hits.length}` : t('book.noHits')}</span>
          <button onClick={() => jumpHit(-1)} disabled={!hits.length}><ChevronLeft size={16} /></button><button onClick={() => jumpHit(1)} disabled={!hits.length}><ChevronRight size={16} /></button></>}
        <span className="sp" />
        <button onClick={() => setScale(s => Math.max(0.5, +(s - 0.2).toFixed(1)))} aria-label="zoom out"><ZoomOut size={18} /></button>
        <span>{Math.round(scale * 100)}%</span>
        <button onClick={() => setScale(s => Math.min(3, +(s + 0.2).toFixed(1)))} aria-label="zoom in"><ZoomIn size={18} /></button>
        <button onClick={toggleFull} aria-label="fullscreen">{full ? <Minimize2 size={18} /> : <Maximize2 size={18} />}</button>
        {onClose && <button onClick={onClose} aria-label="close"><X size={18} /></button>}
      </div>
      <div className="pdfv-body">
        <div className="pdfv-canvas">
          {error ? <p style={{ color: '#fff' }}>{error}</p> : !pdf ? <div style={{ padding: 60 }}><Spinner size={36} /></div> : <canvas ref={canvas} />}
        </div>
        {hits && hits.length > 0 && (
          <aside className="pdfv-hits">
            {hits.map((h, i) => (
              <button key={h.page} className={`pdfv-hit ${i === hitIdx ? 'on' : ''}`} onClick={() => { setHitIdx(i); go(h.page); }}>
                <b>{t('book.page')} {h.page}</b>…{h.snippet}…
              </button>
            ))}
          </aside>
        )}
      </div>
    </div>
  );
}
