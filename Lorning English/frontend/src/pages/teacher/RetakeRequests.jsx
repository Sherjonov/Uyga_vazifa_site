import { useCallback, useEffect, useState } from 'react';
import { Check, RotateCcw, X } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import { Empty, SkeletonList } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDateTime } from '../../utils/format';

const BADGE = { pending: 'badge-warning', approved: 'badge-success', rejected: 'badge-danger' };

/** Qayta topshirish so'rovlari. embedded=true bo'lsa test sahifasi ichida ko'rsatiladi. */
export default function RetakeRequests({ embedded = false, onChange }) {
  const { t, lang } = useLang();
  const toast = useToast();
  const [status, setStatus] = useState('pending');
  const [items, setItems] = useState(null);

  const load = useCallback(() => {
    setItems(null);
    const params = status === 'all' ? {} : { status };
    Promise.all([api.get('/retake', { params }).then(r => r.data.map(x => ({ ...x, kind: 'test' }))).catch(() => []),
                 api.get('/vocab/retake', { params }).then(r => r.data).catch(() => [])])
      .then(([a, b]) => setItems([...a, ...b].sort((x, y) => (y.created_at || '').localeCompare(x.created_at || ''))));
  }, [status]);
  useEffect(() => { load(); }, [load]);

  const act = async (r, action) => {
    let note;
    if (r.kind === 'vocab') { note = window.prompt(t('retake.notePrompt'), '') ; if (note === null) return; }
    try { await (r.kind === 'vocab' ? api.post(`/vocab/retake/${r.id}/${action}`, { note }) : api.post(`/retake/${r.id}/${action}`)); toast.success(t(action === 'approve' ? 'retake.allowedMsg' : 'retake.rejectedMsg')); load(); onChange?.(); } catch (err) { toast.error(errMsg(err)); }
  };

  const body = (
    <div className="stack">
      <div className="tabs" style={{ alignSelf: 'flex-start' }}>
        {['pending', 'all'].map(s => <button key={s} className={`tab ${status === s ? 'active' : ''}`} onClick={() => setStatus(s)}>{t(`retake.tab.${s}`)}</button>)}
      </div>
      {items === null ? <SkeletonList n={2} h={90} /> : items.length === 0 ? <div className="card"><Empty icon={RotateCcw} title={t('retake.none')} /></div> : items.map(r => (
        <div key={`${r.kind}-${r.id}`} className="card stack" style={{ gap: 10 }}>
          <div className="row-between"><div><strong>{r.student_name}</strong> <span className="muted">· {r.kind === 'vocab' ? '📖 ' : ''}{r.test_title}</span></div><span className={`badge ${BADGE[r.status]}`}>{t(`retake.${r.status}`)}</span></div>
          <p className="text-2" style={{ whiteSpace: 'pre-wrap' }}>“{r.reason}”</p>
          {r.teacher_note && <p className="hint">💬 {r.teacher_note}</p>}
          <div className="row-between"><span className="hint">{fmtDateTime(r.created_at, lang)}</span>
            {r.status === 'pending' && <div className="row"><button className="btn btn-success btn-sm" onClick={() => act(r, 'approve')}><Check size={15} /> {t('retake.allow')}</button><button className="btn btn-danger btn-sm" onClick={() => act(r, 'reject')}><X size={15} /> {t('retake.reject')}</button></div>}
          </div>
        </div>
      ))}
    </div>
  );
  if (embedded) return body;
  return <div className="page"><PageHeader icon={RotateCcw} title={t('retake.title')} subtitle={t('retake.subtitle')} />{body}</div>;
}
