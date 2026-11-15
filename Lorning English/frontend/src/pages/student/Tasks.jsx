import { useCallback, useEffect, useState } from 'react';
import { CheckCircle2, ClipboardList, Play, Timer as TimerIcon } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import FileChips from '../../components/FileChips';
import SubmitModal from '../../components/SubmitModal';
import { Empty, SkeletonList } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDateTime } from '../../utils/format';
import './student.css';

export default function Tasks() {
  const { t, lang } = useLang();
  const toast = useToast();
  const [tab, setTab] = useState('pending');
  const [items, setItems] = useState(null);
  const [active, setActive] = useState(null);
  const [starting, setStarting] = useState(null);

  const load = useCallback(() => {
    setItems(null);
    api.get('/assignments/mine', { params: { kind: 'task', status: tab } }).then(r => setItems(r.data)).catch(() => setItems([]));
  }, [tab]);
  useEffect(() => { load(); }, [load]);

  // "Boshlash" bosilganda server taymerni ishga tushiradi va qolgan vaqtni qaytaradi
  const start = async a => {
    setStarting(a.id);
    try {
      const { data } = await api.post(`/assignments/${a.id}/start`);
      setActive(data);
    } catch (err) {
      toast.error(errMsg(err));
      load();
    } finally {
      setStarting(null);
    }
  };

  return (
    <div className="page">
      <PageHeader icon={TimerIcon} title={t('nav.tasks')} subtitle={t('task.subtitle')}
        actions={<div className="tabs">
          <button className={`tab ${tab === 'pending' ? 'active' : ''}`} onClick={() => setTab('pending')}>{t('homework.pending')}</button>
          <button className={`tab ${tab === 'done' ? 'active' : ''}`} onClick={() => setTab('done')}>{t('homework.done')}</button>
        </div>} />
      {items === null ? <SkeletonList n={3} h={120} /> : items.length === 0 ? (
        <div className="card"><Empty icon={tab === 'pending' ? ClipboardList : CheckCircle2} title={tab === 'pending' ? t('task.emptyPending') : t('homework.emptyDone')} /></div>
      ) : (
        <div className="grid grid-auto stagger">
          {items.map(a => (
            <div key={a.id} className="card card-hover assign-card">
              <h3>{a.title}<span className="badge badge-primary"><TimerIcon size={13} /> {a.duration_minutes} {t('time.m')}</span></h3>
              {a.description && (
                <details className="assignment-detail">
                  <summary>📋 {t('assign.text')}</summary>
                  <p>{a.description}</p>
                </details>
              )}
              {tab === 'pending' ? (
                a.expired ? <span className="badge badge-danger" style={{ alignSelf: 'flex-start' }}>{t('task.timeUp')}</span> :
                a.started ? (
                  <button className="btn btn-primary" onClick={() => setActive(a)}><Play size={16} /> {t('task.continue')}</button>
                ) : (
                  <button className="btn btn-primary" disabled={starting === a.id} onClick={() => start(a)}><Play size={16} /> {t('task.start')}</button>
                )
              ) : (
                <>
                  {a.submission?.score != null ? <span className="score-pill" style={{ alignSelf: 'flex-start' }}>{a.submission.score}<small>/ {a.max_score}</small></span> : <span className="badge badge-warning" style={{ alignSelf: 'flex-start' }}>{t('assign.waitingReview')}</span>}
                  {a.submission?.comment && <div className="comment-box"><strong>{t('assign.teacherComment')}:</strong> {a.submission.comment}</div>}
                  <FileChips urls={a.submission?.files || []} />
                  <span className="hint">{fmtDateTime(a.submission?.submitted_at, lang)}</span>
                  {a.can_edit && <button className="btn btn-ghost btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => setActive(a)}>{t('assign.resubmit', { n: a.resubmit_penalty })}</button>}
                </>
              )}
            </div>
          ))}
        </div>
      )}
      {active && <SubmitModal assignment={active} onClose={() => { setActive(null); load(); }} onDone={() => { setActive(null); load(); }} />}
    </div>
  );
}
