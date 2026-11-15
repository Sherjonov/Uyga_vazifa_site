import { useCallback, useEffect, useState } from 'react';
import { BookA, Brain, LockKeyhole, RotateCcw, ShieldCheck, Trophy } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import Modal from '../../components/Modal';
import VocabExam from '../../components/VocabExam';
import Speak from '../../components/Speak';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import '../../styles/extra.css';

export default function Vocab() {
  const { t } = useLang();
  const toast = useToast();
  const [units, setUnits] = useState(null);
  const [study, setStudy] = useState(null);   // {unit, words}
  const [hide, setHide] = useState(true);
  const [exam, setExam] = useState(null);
  const [retake, setRetake] = useState(null); // {unit, reason}
  const [busy, setBusy] = useState(false);

  const [finals, setFinals] = useState([]);
  const [finalExam, setFinalExam] = useState(null); // {id, title}

  const load = useCallback(() => {
    api.get('/vocab/units').then(r => setUnits(r.data)).catch(() => setUnits([]));
    api.get('/vocab/final').then(r => setFinals(r.data)).catch(() => setFinals([]));
  }, []);
  useEffect(() => { load(); }, [load]);

  const openStudy = async u => {
    try { const { data } = await api.get(`/vocab/units/${u.id}/words`); setStudy({ unit: u, words: data.words }); setHide(false); } catch (err) { toast.error(errMsg(err)); }
  };
  // Yakuniy test: ehtimoliy tushadigan 100 ta so'zni yodlash
  const openFinalStudy = async f => {
    try {
      const { data } = await api.get(`/vocab/final/${f.book_id}/words`);
      setStudy({ unit: { final: true, book_id: f.book_id, can_start: f.unlocked && !f.passed && f.attempts_left > 0, title: f.book_title }, words: data.words });
      setHide(false);
    } catch (err) { toast.error(errMsg(err)); }
  };
  const startFinal = f => setFinalExam({ id: f.book_id });
  // Topshirish bosilganda imtihon to'liq ekranda ochiladi
  const startExam = u => {
    try { document.documentElement.requestFullscreen?.()?.catch?.(() => {}); } catch { /* brauzer ruxsat bermasa ham imtihon ochiladi */ }
    setExam(u);
  };
  const closeExam = () => {
    if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {});
    setExam(null);
  };
  const sendRetake = async () => {
    if ((retake.reason || '').trim().length < 5) return toast.error(t('retake.reasonShort'));
    setBusy(true);
    try { await api.post('/vocab/retake', { unit_id: retake.unit.id, reason: retake.reason }); toast.success(t('retake.sent')); setRetake(null); load(); }
    catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  const status = u => {
    if (!u.attempt) return <span className="badge badge-warning">{t('vocab.notDone')}</span>;
    if (u.attempt.kicked_out) return <span className="badge badge-danger">{t('vocab.kicked')}</span>;
    return u.attempt.passed ? <span className="badge badge-success">{t('vocab.passed')} · {u.attempt.score}</span> : <span className="badge badge-danger">{t('vocab.failed')} · {u.attempt.percent}%</span>;
  };

  return (
    <div className="page">
      <PageHeader icon={BookA} title={t('nav.vocab')} subtitle={t('vocab.subtitle')} />
      {units === null ? <SkeletonList n={3} h={100} /> : units.length === 0 ? <div className="card"><Empty icon={BookA} title={t('vocab.none')} text={t('vocab.noneText')} /></div> : (
        <div className="stack stagger">
          {units.map(u => (
            <div key={u.id} className="card stack" style={{ gap: 10 }}>
              <div className="row-between">
                <div><div className="hint">{u.book_title}</div><strong>Unit {u.unit_number}{u.title ? ` — ${u.title}` : ''}</strong></div>
                {status(u)}
              </div>
              <div className="row" style={{ gap: 8 }}>
                <span className="badge">{u.words_count} {t('vocab.words')}</span>
                {!u.open_for_students && <span className="badge badge-warning"><LockKeyhole size={13} /> {t('vocab.locked')}</span>}
                {!u.passed && u.attempts_used > 0 && <span className="badge badge-info">{t('vocab.attemptsLeft', { n: u.attempts_left })}</span>}
                {u.retake && <span className={`badge ${u.retake.status === 'approved' ? 'badge-success' : u.retake.status === 'rejected' ? 'badge-danger' : 'badge-warning'}`}>{t(`retake.${u.retake.status}`)}</span>}
              </div>
              {u.retake?.teacher_note && <p className="hint">💬 {u.retake.teacher_note}</p>}
              {u.attempt && u.attempt.missed.length > 0 && !u.attempt.kicked_out && (
                <details><summary className="hint" style={{ cursor: 'pointer' }}>{t('vx.missed')} ({u.attempt.missed.length})</summary>
                  <table className="vx-words"><tbody>{u.attempt.missed.map((m, i) => <tr key={i}><td>{m.en}</td><td>{m.uz}</td></tr>)}</tbody></table></details>
              )}
              <div className="row">
                <button className="btn btn-ghost" onClick={() => openStudy(u)}><Brain size={16} /> {t('vocab.memorize')}</button>
                {u.can_start
                  ? <button className="btn btn-primary" onClick={() => startExam(u)}>{u.attempt ? <RotateCcw size={16} /> : <ShieldCheck size={16} />} {u.attempt ? t('retake.again') : t('vocab.submit')}</button>
                  : !u.open_for_students
                    ? <button className="btn btn-ghost" disabled><LockKeyhole size={16} /> {t('vocab.locked')}</button>
                    : (!u.retake || u.retake.status === 'rejected' || u.retake.used) && <button className="btn btn-ghost" onClick={() => setRetake({ unit: u, reason: '' })}><RotateCcw size={16} /> {t('retake.ask')}</button>}
              </div>
            </div>
          ))}
        </div>
      )}

      {/* Yakuniy test: har bir lug'at kitobi bo'yicha eng pastda */}
      {finals.map(f => (
        <div key={f.book_id} className="card stack" style={{ gap: 10, marginTop: 18, borderColor: f.unlocked ? 'var(--primary)' : undefined }}>
          <div className="row-between">
            <div><div className="hint">{f.book_title}</div><strong><Trophy size={16} style={{ verticalAlign: -3 }} /> {t('vocab.finalTitle')}</strong></div>
            {f.passed ? <span className="badge badge-success">{t('vocab.passed')} · +{f.score}</span>
              : !f.unlocked ? <span className="badge badge-warning"><LockKeyhole size={13} /> {f.units_passed} / {f.units_total}</span>
                : <span className="badge badge-info">{t('vocab.attemptsLeft', { n: f.attempts_left })}</span>}
          </div>
          <p className="hint">{t('vocab.finalInfo', { w: f.words_count, m: f.max_mistakes, p: f.reward })}</p>
          <div className="row">
            <button className="btn btn-ghost" disabled={!f.unlocked} onClick={() => openFinalStudy(f)}><Brain size={16} /> {t('vocab.memorize')}</button>
            <button className="btn btn-primary" disabled={!f.unlocked || f.passed || f.attempts_left <= 0} onClick={() => startFinal(f)}><ShieldCheck size={16} /> {t('vocab.submit')}</button>
          </div>
          {!f.unlocked && <p className="hint">{t('vocab.finalLocked', { n: f.units_total })}</p>}
        </div>
      ))}

      <Modal open={!!study} onClose={() => setStudy(null)} size="lg"
        title={study ? (study.unit.final ? `${t('vocab.finalTitle')} — ${study.unit.title}` : `Unit ${study.unit.unit_number}`) : ''}
        footer={study && <div className="row-between" style={{ width: '100%' }}>
          <span className="hint">{study.words.length} {t('vocab.words')}</span>
          <div className="row">
            <button className="btn btn-ghost" onClick={() => setHide(h => !h)}>{hide ? t('vocab.showUz') : t('vocab.hideUz')}</button>
            {study.unit.can_start && <button className="btn btn-primary" onClick={() => {
              const u = study.unit; setStudy(null);
              if (u.final) startFinal({ book_id: u.book_id }); else startExam(u);
            }}><ShieldCheck size={16} /> {t('vocab.submit')}</button>}
          </div>
        </div>}>
        {study && <div className="vx-study">
          <table className="vx-words vx-study-table">
            <thead><tr><th>#</th><th>English</th><th>O'zbekcha</th><th /></tr></thead>
            <tbody>{study.words.map((w, i) => (
              <tr key={i}><td className="hint">{i + 1}</td><td><strong>{w.en}</strong></td>
                <td><span className={hide ? 'vx-hide' : ''}>{w.uz}</span></td>
                <td style={{ width: 44 }}><Speak text={w.en} lang="en" /></td></tr>
            ))}</tbody>
          </table>
        </div>}
      </Modal>

      <Modal open={!!retake} onClose={() => setRetake(null)} size="sm" title={t('retake.ask')}
        footer={<><button className="btn btn-ghost" onClick={() => setRetake(null)}>{t('common.cancel')}</button>
          <button className="btn btn-primary" disabled={busy} onClick={sendRetake}>{busy ? <Spinner size={16} /> : null} {t('retake.send')}</button></>}>
        {retake && <div className="field" style={{ marginBottom: 0 }}><label>{t('retake.reason')}</label>
          <textarea className="textarea" autoFocus maxLength={500} value={retake.reason} onChange={e => setRetake({ ...retake, reason: e.target.value })} /></div>}
      </Modal>

      {exam && <VocabExam unit={exam} onClose={closeExam} onFinished={load} />}
      {finalExam && <VocabExam kind="final" unit={finalExam} onClose={() => { if (document.fullscreenElement) document.exitFullscreen?.().catch(() => {}); setFinalExam(null); }} onFinished={load} />}
    </div>
  );
}
