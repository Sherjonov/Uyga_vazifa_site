import { useCallback, useEffect, useMemo, useState } from 'react';
import { BookOpenCheck, CheckCircle2 } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import SubmitModal from '../../components/SubmitModal';
import HwCard from '../../components/HwCard';
import { Empty, SkeletonList } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import api from '../../api/axios';
import '../../components/work.css';
import './student.css';

export default function Homework({ kind = 'homework' }) {
  const { t } = useLang();
  const [tab, setTab] = useState('current');
  const [data, setData] = useState(null); // { pending: [], done: [] }
  const [sel, setSel] = useState(null);

  const load = useCallback(() => {
    const get = status => api.get('/assignments/mine', { params: { kind, status } }).then(r => r.data);
    Promise.all([get('pending'), get('done')]).then(([pending, done]) => setData({ pending, done })).catch(() => setData({ pending: [], done: [] }));
  }, [kind]);
  useEffect(() => { load(); }, [load]);

  // Joriy = topshirilmagan + tekshirilmayotgan; Baholangan = ball qo'yilgan
  const { current, graded } = useMemo(() => {
    if (!data) return { current: [], graded: [] };
    const checking = data.done.filter(a => a.submission?.score == null);
    return { current: [...data.pending.map(a => ({ a, mode: 'pending' })), ...checking.map(a => ({ a, mode: 'checking' }))],
             graded: data.done.filter(a => a.submission?.score != null).map(a => ({ a, mode: 'graded' })) };
  }, [data]);

  const shown = tab === 'current' ? current : graded;

  return (
    <div className="page">
      <PageHeader icon={BookOpenCheck} title={kind === 'extra' ? t('nav.extra') : t('nav.homework')} subtitle={kind === 'extra' ? t('extra.studentSub') : t('homework.subtitle')} />
      <div className="wk-tabs">
        <button className={`wk-tab ${tab === 'current' ? 'active' : ''}`} onClick={() => setTab('current')}>📝 {t('wk.current')} ({current.length})</button>
        <button className={`wk-tab ${tab === 'graded' ? 'active' : ''}`} onClick={() => setTab('graded')}>✅ {t('wk.graded')} ({graded.length})</button>
      </div>

      {data === null ? <SkeletonList n={2} h={260} /> : shown.length === 0 ? (
        <div className="card"><Empty icon={tab === 'current' ? BookOpenCheck : CheckCircle2}
          title={tab === 'current' ? t('homework.emptyPending') : t('wk.emptyGraded')} text={tab === 'current' ? t('homework.emptyPendingText') : ''} /></div>
      ) : (
        <div className="wk-list stagger">
          {shown.map(({ a, mode }) => <HwCard key={a.id} a={a} mode={mode} onSubmit={setSel} />)}
        </div>
      )}
      {sel && <SubmitModal assignment={sel} onClose={() => setSel(null)} onDone={() => { setSel(null); load(); }} />}
    </div>
  );
}
