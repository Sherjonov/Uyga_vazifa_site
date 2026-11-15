import { useLang } from '../context/LangContext';
import { fmtDate, initials, num } from '../utils/format';

const MEDALS = ['🥇', '🥈', '🥉'];

/** Oxirgi darsning eng faol qatnashganlari (har yangi darsda yangilanadi) */
export default function ActiveLesson({ data }) {
  const { t, lang } = useLang();
  if (!data?.group) return null;
  const top = data.top || [];
  const order = top.length === 3 ? [top[1], top[0], top[2]] : top;
  const inTop = data.me && data.me.rank <= 3;
  return (
    <div className="act anim-scale-in">
      <h2>🏆 {t('home.activeTitle')}</h2>
      <p className="act-sub">{[data.lesson, data.date ? fmtDate(data.date, lang) : null].filter(Boolean).join(' · ') || data.group.name}</p>
      {top.length === 0 ? <div className="act-note">{t('home.activeEmpty')}</div> : (
        <>
          <div className="act-note">{inTop ? t('home.activeCongrats') : t('home.activeNext')}</div>
          <div className="act-podium">
            {order.map(p => (
              <div key={p.id} className={`act-item r${p.rank}`}>
                <span className="act-medal">{MEDALS[p.rank - 1]}</span>
                <span className="act-ava">{initials(p.name)}</span>
                <strong>{p.name}{p.is_me ? ` (${t('rating.you')})` : ''}</strong>
                <span className="act-title">{t(`home.badge${p.rank}`)}</span>
                <div className="act-box">
                  <span style={{ fontSize: '1.1rem' }}>{p.rank}</span>
                  <b>{num(p.total, 1)}</b><small>{t('home.activePts')}</small>
                  <div className="act-chips"><span>📝 {num(p.test, 0)}</span><span>⏱ {num(p.task, 0)}</span><span>📘 {num(p.homework, 0)}</span></div>
                </div>
              </div>
            ))}
          </div>
        </>
      )}
      {data.me && !inTop && <p className="act-me">{t('home.activeMe', { rank: data.me.rank, n: num(data.me.total, 1) })}</p>}
    </div>
  );
}
