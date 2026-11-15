import { useCallback, useEffect, useRef, useState } from 'react';
import { useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, ArrowRight, CheckCircle2, Flag, ShieldAlert } from 'lucide-react';
import Timer from '../../components/Timer';
import Modal from '../../components/Modal';
import { PageLoader, Spinner } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { num } from '../../utils/format';
import './student.css';

export default function TestRun() {
  const { id } = useParams();
  const nav = useNavigate();
  const { t } = useLang();
  const toast = useToast();
  const [data, setData] = useState(null);
  const [error, setError] = useState('');
  const [answers, setAnswers] = useState({});
  const [cur, setCur] = useState(0);
  const [confirm, setConfirm] = useState(false);
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState(null);
  const answersRef = useRef({});
  const saveTimer = useRef(null);
  const finished = useRef(false);
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return; // StrictMode ikki marta chaqirmasligi uchun
    started.current = true;
    api.post(`/tests/${id}/start`)
      .then(r => { setData(r.data); setAnswers(r.data.answers || {}); answersRef.current = r.data.answers || {}; })
      .catch(err => setError(errMsg(err)));
  }, [id]);

  // Javoblar o'zgarganda serverga avtomatik saqlanadi (internet uzilsa ham yo'qolmasin)
  const choose = (qid, idx) => {
    const next = { ...answersRef.current, [qid]: idx };
    answersRef.current = next;
    setAnswers(next);
    clearTimeout(saveTimer.current);
    saveTimer.current = setTimeout(() => api.put(`/tests/attempts/${data.attempt_id}/answers`, { answers: next }).catch(() => {}), 700);
  };

  useEffect(() => {
    if (!data || result) return undefined;
    const warn = e => { e.preventDefault(); e.returnValue = ''; };
    window.addEventListener('beforeunload', warn);
    return () => window.removeEventListener('beforeunload', warn);
  }, [data, result]);

  const finish = useCallback(async (auto = false) => {
    if (finished.current || !data) return;
    finished.current = true;
    setBusy(true);
    try {
      const { data: res } = await api.post(`/tests/attempts/${data.attempt_id}/finish`, { answers: answersRef.current });
      setResult(res);
      setConfirm(false);
    } catch (err) {
      finished.current = false;
      toast.error(errMsg(err));
      if (auto) setError(errMsg(err));
    } finally { setBusy(false); }
  }, [data, toast]);

  if (error) {
    return (
      <div className="page test-shell"><div className="card center stack" style={{ alignItems: 'center', padding: 40 }}>
        <div className="stat-icon danger"><ShieldAlert size={26} /></div><h2>{error}</h2>
        <button className="btn btn-primary" onClick={() => nav('/student/tests')}><ArrowLeft size={16} /> {t('common.back')}</button>
      </div></div>
    );
  }
  if (!data) return <PageLoader />;

  if (result) {
    const shown = result.counted ? result.score : result.practice_score;
    return (
      <div className="page test-shell">
        <div className="card center stack" style={{ alignItems: 'center', padding: 36, gap: 20 }}>
          <CheckCircle2 size={44} color="var(--success)" />
          <h2>{t('test.finished')}</h2>
          <div className="ring" style={{ '--p': result.percent }}><div><strong>{num(shown, 2)}</strong><span className="muted">/ 10</span></div></div>
          <p className="text-2">{t('test.correct', { c: result.correct, n: result.total })} · {num(result.percent, 0)}%</p>
          <div className={`alert ${result.counted ? 'alert-success' : 'alert-info'}`}>{result.counted ? t('test.counted') : t('test.practiceNote')}</div>
          <button className="btn btn-primary" onClick={() => nav('/student/tests')}>{t('test.backToTests')}</button>
        </div>
      </div>
    );
  }

  const qs = data.questions;
  const q = qs[cur];
  const answered = Object.keys(answers).length;
  const seconds = Math.max(0, (new Date(data.deadline_at) - new Date(data.server_time)) / 1000);

  return (
    <div className="page test-shell">
      <div className="row-between" style={{ marginBottom: 18 }}>
        <div><h2>{data.test.title}</h2><span className="hint">{data.counted ? t('test.countedBadge') : t('test.practiceBadge')}</span></div>
        <Timer seconds={seconds} total={data.test.duration_minutes * 60} onEnd={() => finish(true)} />
      </div>
      <div className="row" style={{ marginBottom: 16, flexWrap: 'nowrap' }}>
        <div className="progress spacer"><span style={{ width: `${(answered / qs.length) * 100}%` }} /></div>
        <span className="mono muted">{answered}/{qs.length}</span>
      </div>
      <div className="card q-card anim-scale-in" key={q.id}>
        <span className="badge badge-primary" style={{ marginBottom: 12 }}>{t('test.question')} {cur + 1} / {qs.length}</span>
        <div className="q-text">{q.text}</div>
        {q.options.map((o, i) => (
          <button key={i} className={`opt ${answers[q.id] === i ? 'picked' : ''}`} onClick={() => choose(q.id, i)}>
            <span className="opt-letter">{String.fromCharCode(65 + i)}</span><span>{o}</span>
          </button>
        ))}
        <div className="row-between" style={{ marginTop: 18 }}>
          <button className="btn btn-ghost" disabled={cur === 0} onClick={() => setCur(c => c - 1)}><ArrowLeft size={16} /> {t('common.back')}</button>
          {cur < qs.length - 1
            ? <button className="btn btn-primary" onClick={() => setCur(c => c + 1)}>{t('common.next')} <ArrowRight size={16} /></button>
            : <button className="btn btn-primary" onClick={() => setConfirm(true)}><Flag size={16} /> {t('test.finish')}</button>}
        </div>
      </div>
      <div className="card" style={{ marginTop: 16 }}>
        <div className="row-between" style={{ marginBottom: 12 }}><strong>{t('test.palette')}</strong><button className="btn btn-sm btn-ghost" onClick={() => setConfirm(true)}><Flag size={14} /> {t('test.finish')}</button></div>
        <div className="palette">{qs.map((x, i) => <button key={x.id} className={`pal ${answers[x.id] != null ? 'done' : ''} ${i === cur ? 'cur' : ''}`} onClick={() => setCur(i)}>{i + 1}</button>)}</div>
      </div>
      <Modal open={confirm} onClose={() => setConfirm(false)} title={t('test.finishTitle')} size="sm"
        footer={<><button className="btn btn-ghost" onClick={() => setConfirm(false)}>{t('common.cancel')}</button><button className="btn btn-primary" disabled={busy} onClick={() => finish(false)}>{busy && <Spinner size={16} />} {t('test.finish')}</button></>}>
        <p>{answered < qs.length ? t('test.unanswered', { n: qs.length - answered }) : t('test.confirmFinish')}</p>
      </Modal>
    </div>
  );
}
