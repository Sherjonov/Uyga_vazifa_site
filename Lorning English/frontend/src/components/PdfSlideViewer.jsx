import { useCallback, useEffect, useRef, useState } from 'react';
import { ChevronLeft, ChevronRight, Maximize2, Minimize2 } from 'lucide-react';
import './PdfSlideViewer.css';

/** slides: [{page, url}] — backend PDF sahifalarini rasmga aylantirgan */
export default function PdfSlideViewer({ slides = [], title }) {
  const [index, setIndex] = useState(0);
  const [full, setFull] = useState(false);
  const [loaded, setLoaded] = useState(false);
  const box = useRef(null);
  const touch = useRef(null);
  const total = slides.length;

  const go = useCallback(d => setIndex(i => Math.min(total - 1, Math.max(0, i + d))), [total]);

  useEffect(() => {
    const onKey = e => {
      if (['INPUT', 'TEXTAREA', 'SELECT'].includes(document.activeElement?.tagName)) return;
      if (e.key === 'ArrowRight') go(1);
      if (e.key === 'ArrowLeft') go(-1);
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [go]);

  useEffect(() => {
    const onFs = () => setFull(document.fullscreenElement === box.current);
    document.addEventListener('fullscreenchange', onFs);
    return () => document.removeEventListener('fullscreenchange', onFs);
  }, []);

  useEffect(() => {
    setLoaded(false);
    const next = slides[index + 1];
    if (next) { const img = new Image(); img.src = next.url; }
  }, [index, slides]);

  const toggleFull = () => {
    if (document.fullscreenElement) document.exitFullscreen();
    else box.current?.requestFullscreen?.();
  };

  if (!total) return null;
  const onTouchEnd = e => {
    if (touch.current == null) return;
    const dx = e.changedTouches[0].clientX - touch.current;
    if (Math.abs(dx) > 50) go(dx < 0 ? 1 : -1);
    touch.current = null;
  };

  return (
    <div className={`slides ${full ? 'is-full' : ''}`} ref={box}>
      {title && <div className="slides-title">{title}</div>}
      <div className="slides-stage" onTouchStart={e => (touch.current = e.touches[0].clientX)} onTouchEnd={onTouchEnd}>
        <button className="slides-nav prev" onClick={() => go(-1)} disabled={index === 0} aria-label="prev"><ChevronLeft size={26} /></button>
        <div className="slides-frame">
          {!loaded && <span className="spinner" style={{ position: 'absolute', width: 34, height: 34 }} />}
          <img key={slides[index].url} src={slides[index].url} alt={`${index + 1}`} onLoad={() => setLoaded(true)} className={loaded ? 'ready' : ''} draggable={false} />
        </div>
        <button className="slides-nav next" onClick={() => go(1)} disabled={index === total - 1} aria-label="next"><ChevronRight size={26} /></button>
      </div>
      <div className="slides-bar">
        <span className="slides-count mono">{index + 1} / {total}</span>
        <div className="progress slides-progress"><span style={{ width: `${((index + 1) / total) * 100}%` }} /></div>
        <button className="btn btn-ghost btn-icon btn-sm" onClick={toggleFull} aria-label="fullscreen">{full ? <Minimize2 size={17} /> : <Maximize2 size={17} />}</button>
      </div>
    </div>
  );
}
