import { useEffect, useRef, useState } from 'react';
import { Clock } from 'lucide-react';
import './Timer.css';

const pad = n => String(n).padStart(2, '0');
export const fmtClock = sec => {
  const s = Math.max(0, Math.ceil(sec));
  const h = Math.floor(s / 3600);
  const m = Math.floor((s % 3600) / 60);
  return `${h > 0 ? `${pad(h)}:` : ''}${pad(m)}:${pad(s % 60)}`;
};

/** seconds — serverdan kelgan qolgan vaqt. Tugaganda onEnd bir marta chaqiriladi. */
export default function Timer({ seconds, total, onEnd, label }) {
  const deadline = useRef(Date.now() + seconds * 1000);
  const ended = useRef(false);
  const [left, setLeft] = useState(seconds);
  const onEndRef = useRef(onEnd);
  onEndRef.current = onEnd;

  useEffect(() => {
    deadline.current = Date.now() + seconds * 1000;
    ended.current = false;
    const tick = () => {
      const rest = (deadline.current - Date.now()) / 1000;
      setLeft(Math.max(0, rest));
      if (rest <= 0 && !ended.current) {
        ended.current = true;
        onEndRef.current?.();
      }
    };
    tick();
    const id = setInterval(tick, 250);
    return () => clearInterval(id);
  }, [seconds]);

  const full = total || seconds || 1;
  const pct = Math.min(100, Math.max(0, (left / full) * 100));
  const state = left <= 0 ? 'over' : left <= 60 || pct < 15 ? 'danger' : pct < 35 ? 'warn' : '';
  return (
    <div className={`timer ${state}`}>
      <Clock size={18} />
      <div className="timer-body">
        {label && <span className="timer-label">{label}</span>}
        <strong className="mono">{fmtClock(left)}</strong>
      </div>
      <div className="timer-bar"><span style={{ width: `${pct}%` }} /></div>
    </div>
  );
}
