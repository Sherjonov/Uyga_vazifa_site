import { useCallback, useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { FileCheck2, Play, RotateCcw, Send, Timer } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import Modal from '../../components/Modal';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { num } from '../../utils/format';
import './student.css';

const RETAKE_BADGE = { pending: ['badge-warning', 'retake.pending'], approved: ['badge-success', 'retake.approved'], rejected: ['badge-danger', 'retake.rejected'] };

export default function Tests() {
  const { t } = useLang();
  const toast = useToast();
  const nav = useNavigate();
  const [items, setItems] = useState(null);
  const [req, setReq] = useState(null);
  const [reason, setReason] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => api.get('/tests/mine').then(r => setItems(r.data)).catch(() => setItems([])), []);
  useEffect(() => { load(); }, [load]);

  const sendRequest = async () => {
    if (reason.trim().length < 5) return toast.error(t('retake.reasonShort'));
    setBusy(true);
    try {
      await api.post('/retake', { test_id: req.id, reason: reason.trim() });
      toast.success(t('retake.sent'));
      setReq(null); setReason(''); load();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <div className="page">
      <PageHeader icon={FileCheck2} title={t('nav.tests')} subtitle={t('tests.subtitle')} />
      <div className="alert alert-info" style={{ marginBottom: 20 }}>{t('tests.rule')}</div>
      {items === null ? <SkeletonList n={3} h={130} /> : items.length === 0 ? <div className="card"><Empty icon={FileCheck2} title={t('tests.empty')} /></div> : (
        <div className="grid grid-auto stagger">
          {items.map(x => {
            const rb = x.retake_status && RETAKE_BADGE[x.retake_status];
            return (
              <div key={x.id} className="card card-hover assign-card">
                <h3>{x.title}</h3>
                <div className="assign-meta">
                  <span className="badge"><Timer size={13} /> {x.duration_minutes} {t('time.m')}</span>
                  <span className="badge">{x.questions_count} {t('tests.questions')}</span>
                  {rb && <span className={`badge ${rb[0]}`}>{t(rb[1])}</span>}
                </div>
                {x.state === 'finished' && (
                  <div className="row"><span className="score-pill">{num(x.score, 2)}<small>/ 10</small></span><span className="hint">{num(x.percent, 0)}% · {t('tests.counted')}</span></div>
                )}
                {x.state === 'needs_retake' && <div className="alert alert-warning">{t('tests.unfinished')}</div>}
                <div className="row">
                  {(x.state === 'available' || x.state === 'retake_approved') && <button className="btn btn-primary" onClick={() => nav(`/student/tests/${x.id}/run`)}><Play size={16} /> {x.state === 'retake_approved' ? t('tests.restart') : t('tests.start')}</button>}
                  {x.state === 'in_progress' && <button className="btn btn-primary" onClick={() => nav(`/student/tests/${x.id}/run`)}><Play size={16} /> {t('tests.continue')}</button>}
                  {x.state === 'finished' && <button className="btn btn-ghost" onClick={() => nav(`/student/tests/${x.id}/run`)}><RotateCcw size={16} /> {t('tests.practice')}</button>}
                  {x.state === 'needs_retake' && x.retake_status !== 'pending' && <button className="btn btn-primary" onClick={() => setReq(x)}><Send size={16} /> {t('retake.request')}</button>}
                </div>
              </div>
            );
          })}
        </div>
      )}
      <Modal open={!!req} onClose={() => setReq(null)} title={t('retake.request')} size="sm"
        footer={<><button className="btn btn-ghost" onClick={() => setReq(null)}>{t('common.cancel')}</button><button className="btn btn-primary" disabled={busy} onClick={sendRequest}>{busy ? <Spinner size={16} /> : <Send size={16} />} {t('common.send')}</button></>}>
        <p className="text-2" style={{ marginBottom: 14 }}>{req?.title}</p>
        <div className="field" style={{ marginBottom: 0 }}><label>{t('retake.reason')}</label><textarea className="textarea" value={reason} onChange={e => setReason(e.target.value)} placeholder={t('retake.reasonPh')} /></div>
      </Modal>
    </div>
  );
}
