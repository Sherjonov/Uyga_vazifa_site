import { useEffect, useState } from 'react';
import { Clock3 } from 'lucide-react';
import { Empty, SkeletonList } from './Loader';
import { useLang } from '../context/LangContext';
import api, { errMsg } from '../api/axios';
import { fmtDateTime, num } from '../utils/format';
import './ScoreHistory.css';

const TYPES = {
  test: 'history.type.test',
  homework: 'history.type.homework',
  task: 'history.type.task',
  grid: 'history.type.grid',
  penalty: 'history.type.penalty',
  resubmit: 'history.type.resubmit'
};

export default function ScoreHistory({ endpoint }) {
  const { t, lang } = useLang();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');

  useEffect(() => {
    let active = true;
    setData(null);
    setError('');
    api.get(endpoint).then(r => {
      if (active) setData(r.data);
    }).catch(err => {
      if (active) setError(errMsg(err));
    });
    return () => { active = false; };
  }, [endpoint]);

  if (error) return <div className="alert alert-danger">{error}</div>;
  if (!data) return <SkeletonList n={3} h={68} />;

  const { summary, items } = data;
  return (
    <div className="stack" style={{ gap: 16 }}>
      <div className="grid grid-3">
        {[
          [t('home.fromTests'), summary.tests],
          [t('home.fromAssignments'), summary.assignments],
          [t('home.fromGrid'), summary.grid],
          [t('home.penalties'), -summary.penalties],
          [t('home.resubmits'), -summary.resubmits],
          [t('home.total'), summary.total]
        ].map(([label, score]) => (
          <div className="card score-history-stat" key={label}>
            <span className="hint">{label}</span>
            <strong className="mono">{score > 0 ? '+' : ''}{num(score, 1)}</strong>
          </div>
        ))}
      </div>

      {items.length === 0 ? (
        <div className="card"><Empty icon={Clock3} title={t('history.empty')} /></div>
      ) : (
        <div className="stack score-history-list">
          {items.map(item => (
            <article key={item.id} className="card score-history-event">
              <span className={`score-history-icon ${item.score < 0 ? 'negative' : ''}`}>
                {item.type === 'test' ? '📝' : item.type === 'grid' ? '📊' : item.type === 'penalty' ? '⚠️' : '📚'}
              </span>
              <div className="spacer">
                <strong>{item.title || t(TYPES[item.type] || 'history.type.grid')}</strong>
                <div className="hint">{t(TYPES[item.type] || 'history.type.grid')} · {fmtDateTime(item.date, lang)}</div>
              </div>
              <strong className={`mono score-history-points ${item.score < 0 ? 'negative' : ''}`}>
                {item.score > 0 ? '+' : ''}{num(item.score, 1)}{item.max_score != null ? ` / ${num(item.max_score, 1)}` : ''}
              </strong>
            </article>
          ))}
        </div>
      )}
    </div>
  );
}
