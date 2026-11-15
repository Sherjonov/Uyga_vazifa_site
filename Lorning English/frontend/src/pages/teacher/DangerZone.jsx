import { useCallback, useEffect, useState } from 'react';
import { ShieldAlert, ShieldCheck } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import { Empty, SkeletonList } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import api from '../../api/axios';
import { initials, num } from '../../utils/format';
import './teacher.css';

const REASON_CLS = { missed_homework: 'badge-warning', low_tests: 'badge-danger', absences: 'badge-danger', score_drop: 'badge-warning', inactive: 'badge-info' };

export default function DangerZone() {
  const { t } = useLang();
  const { groups, loading: gl } = useGroups();
  const [groupId, setGroupId] = useState(null);
  const [items, setItems] = useState(null);

  const load = useCallback(() => {
    setItems(null);
    api.get('/danger-zone', { params: groupId ? { group_id: groupId } : {} }).then(r => setItems(r.data)).catch(() => setItems([]));
  }, [groupId]);
  useEffect(() => { if (!gl) load(); }, [gl, load]);

  return (
    <div className="page">
      <PageHeader icon={ShieldAlert} title={t('nav.dangerZone')} subtitle={t('danger.subtitle')}
        actions={groups.length > 0 && <GroupSelect all allLabel={t('common.allGroups')} groups={groups} value={groupId} onChange={setGroupId} />} />
      {items === null ? <SkeletonList n={3} h={130} /> : items.length === 0 ? (
        <div className="card"><Empty icon={ShieldCheck} title={t('danger.none')} text={t('danger.noneText')} /></div>
      ) : (
        <div className="grid grid-auto stagger" style={{ gridTemplateColumns: 'repeat(auto-fill, minmax(340px, 1fr))' }}>
          {items.map(it => (
            <div key={`${it.student.id}-${it.group.id}`} className={`card danger-card lvl-${it.level}`}>
              <div className="row" style={{ flexWrap: 'nowrap' }}>
                <span className="avatar">{initials(it.student.name)}</span>
                <div className="spacer"><strong>{it.student.name}</strong><div className="hint">{it.group.name} · {t('students.score')}: {num(it.student.total_score, 1)}</div></div>
                <span className={`badge ${it.level === 'high' ? 'badge-danger' : it.level === 'medium' ? 'badge-warning' : 'badge-info'}`}>{t(`danger.level.${it.level}`)}</span>
              </div>
              <div className="row" style={{ gap: 6 }}>
                {it.reasons.map(r => <span key={r.code} className={`badge ${REASON_CLS[r.code]}`}>{t(`danger.${r.code}`, { v: r.value ?? '∞', th: r.threshold })}</span>)}
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
