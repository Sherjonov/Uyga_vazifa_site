import { useCallback, useEffect, useState } from 'react';
import { Trophy } from 'lucide-react';
import GroupSelect from './GroupSelect';
import { Empty, SkeletonList } from './Loader';
import useGroups from '../utils/useGroups';
import { useLang } from '../context/LangContext';
import api from '../api/axios';
import { initials, num } from '../utils/format';
import './RatingBoard.css';

const MEDAL = ['🥇', '🥈', '🥉'];

/** Reyting jadvali: guruh va umumiy. Birinchi 3 o'rin alohida, o'z o'rningiz belgilanadi. */
export default function RatingBoard({ allowAll = true }) {
  const { t } = useLang();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [scope, setScope] = useState('group');
  const [data, setData] = useState(null);

  const effective = scope === 'group' && !groupId ? 'all' : scope;
  const load = useCallback(() => {
    setData(null);
    const params = effective === 'group' ? { scope: 'group', group_id: groupId } : { scope: 'all' };
    api.get('/rating', { params }).then(r => setData(r.data)).catch(() => setData({ items: [], me: null }));
  }, [effective, groupId]);
  useEffect(() => { if (!gl) load(); }, [gl, load]);

  const top = data?.items.slice(0, 3) || [];
  const rest = data?.items.slice(3) || [];
  const order = top.length === 3 ? [top[1], top[0], top[2]] : top;

  return (
    <div className="stack" style={{ gap: 22 }}>
      <div className="row-between">
        {allowAll ? (
          <div className="tabs">
            <button className={`tab ${scope === 'group' ? 'active' : ''}`} onClick={() => setScope('group')}>{t('rating.group')}</button>
            <button className={`tab ${scope === 'all' ? 'active' : ''}`} onClick={() => setScope('all')}>{t('rating.all')}</button>
          </div>
        ) : <span />}
        {scope === 'group' && <GroupSelect groups={groups} value={groupId} onChange={setGroupId} />}
      </div>

      {data === null ? <SkeletonList n={5} h={64} /> : data.items.length === 0 ? <div className="card"><Empty icon={Trophy} title={t('rating.empty')} /></div> : (
        <>
          {data.me && <div className="rating-me card"><span className="muted">{t('rating.yourPlace')}</span><strong>#{data.me.rank}</strong><span className="badge badge-primary">{num(data.me.score, 1)} {t('rating.points')}</span></div>}
          <div className="podium">
            {order.map(p => {
              const i = data.items.indexOf(p);
              return (
                <div key={p.id} className={`podium-item p${i + 1} ${p.is_me ? 'me' : ''}`}>
                  <span className="podium-medal">{MEDAL[i]}</span>
                  <span className="avatar avatar-lg">{initials(p.name)}</span>
                  <strong>{p.name}</strong>
                  <span className="podium-score">{num(p.score, 1)}</span>
                  <div className="podium-bar" />
                </div>
              );
            })}
          </div>
          <div className="stack stagger" style={{ gap: 8 }}>
            {rest.map(r => (
              <div key={r.id} className={`list-item rating-row ${r.is_me ? 'me' : ''}`}>
                <span className="rank mono">{r.rank}</span>
                <span className="avatar">{initials(r.name)}</span>
                <strong className="spacer">{r.name}{r.is_me && <span className="badge badge-primary" style={{ marginLeft: 8 }}>{t('rating.you')}</span>}</strong>
                <span className="mono" style={{ fontWeight: 700 }}>{num(r.score, 1)}</span>
              </div>
            ))}
            {data.me && data.me.rank > 100 && <p className="muted center">…</p>}
          </div>
        </>
      )}
    </div>
  );
}
