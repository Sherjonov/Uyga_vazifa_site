import { useCallback, useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { CheckCircle2, OctagonX, ShieldAlert, XCircle } from 'lucide-react';
import { Spinner } from './Loader';
import Speak from './Speak';
import { useLang } from '../context/LangContext';
import api, { errMsg } from '../api/axios';
import '../styles/extra.css';
import '../pages/student/student.css';  // test sahifasi bilan bir xil dizayn (q-card, opt, palette)

/**
 * Lug'at imtihoni. Barcha savollar variantlari bilan jadvalda; javob bir marta tanlanadi, server xatolarni sanaydi.
 *  kind="unit"  : 17 lug'at + 3 amaliy savol, 3 ta xatoda to'xtaydi (avtomatik to'liq ekran)
 *  kind="final" : 100 ta so'z, 10 tagacha xato mumkin; qat'iy rejim (full screen + ogohlantirish) ixtiyoriy
 */
export default function VocabExam({ unit, kind = 'unit', onClose, onFinished }) {
  const { t } = useLang();
  const final = kind === 'final';
  const base = final ? '/vocab/final-attempts' : '/vocab/attempts';
  const [phase, setPhase] = useState(final ? 'intro' : 'starting');
  const [strict, setStrict] = useState(false);
  const [error, setError] = useState('');
  const [attempt, setAttempt] = useState(null);
  const [answers, setAnswers] = useState({});
  const [cur, setCur] = useState(0);
  const [result, setResult] = useState(null);
  const [busy, setBusy] = useState(false);
  const [warn, setWarn] = useState(0);        // ko'rsatilayotgan ogohlantirish raqami (0 = yo'q)
  const attemptRef = useRef(null);
  const startingRef = useRef(false);
  const submittingRef = useRef(false);
  const warnOpenRef = useRef(false);
  const strictRef = useRef(false);
  const phaseRef = useRef(phase);
  const root = useRef(null);
  phaseRef.current = phase;

  // Sahifa to'liq ekranni to'sib qo'ymasligi uchun fon aylantirilmaydi
  useEffect(() => {
    const prev = document.body.style.overflow;
    document.body.style.overflow = 'hidden';
    return () => { document.body.style.overflow = prev; };
  }, []);

  const goFullscreen = useCallback(() => {
    if (document.fullscreenElement) return;
    try { root.current?.requestFullscreen?.()?.catch?.(() => {}); } catch { /* ruxsat berilmasa ham imtihon butun oynada ochiladi */ }
  }, []);

  const begin = useCallback(async (useStrict = false) => {
    if (startingRef.current) return;
    startingRef.current = true;
    setError('');
    setPhase('starting');
    try {
      const { data } = final
        ? await api.post(`/vocab/final/${unit.id}/start`, { strict: useStrict })
        : await api.post(`/vocab/units/${unit.id}/start`);
      attemptRef.current = data.attempt_id;
      strictRef.current = final && useStrict;
      setAttempt(data);
      setAnswers(data.answers || {});
      setPhase('exam');
    } catch (err) {
      setError(errMsg(err));
      setPhase('error');
    } finally {
      startingRef.current = false;
    }
  }, [unit.id, final]);

  useEffect(() => { if (!final) begin(); }, [begin, final]);

  // Qat'iy rejim (faqat yakuniy testda, ixtiyoriy): boshqa oynaga/tabga o'tish yoki to'liq ekrandan chiqish -> ogohlantirish
  useEffect(() => {
    if (!final || phase !== 'exam' || !strictRef.current) return undefined;
    const violation = () => {
      if (warnOpenRef.current || phaseRef.current !== 'exam') return;
      warnOpenRef.current = true;
      api.post(`${base}/${attemptRef.current}/violation`).then(r => setWarn(r.data.warnings || 1)).catch(() => setWarn(w => w + 1));
    };
    const onVisibility = () => { if (document.hidden) violation(); };
    const onFullscreen = () => { if (!document.fullscreenElement) violation(); };
    document.addEventListener('visibilitychange', onVisibility);
    document.addEventListener('fullscreenchange', onFullscreen);
    window.addEventListener('blur', violation);
    return () => {
      document.removeEventListener('visibilitychange', onVisibility);
      document.removeEventListener('fullscreenchange', onFullscreen);
      window.removeEventListener('blur', violation);
    };
  }, [final, phase, base]);

  const closeWarn = () => { warnOpenRef.current = false; setWarn(0); goFullscreen(); };

  const finish = useCallback(async (current) => {
    if (!attemptRef.current || submittingRef.current) return;
    submittingRef.current = true;
    setBusy(true);
    setError('');
    try {
      const { data } = await api.post(`${base}/${attemptRef.current}/submit`, final ? {} : { answers: current });
      setResult(data);
      setPhase('result');
    } catch (err) {
      setError(errMsg(err));
    } finally {
      submittingRef.current = false;
      setBusy(false);
    }
  }, [base, final]);

  // Javob bir marta tanlanadi va qulflanadi; server xatolarni sanaydi
  const choose = async (question, optionIndex) => {
    if (answers[question.id] !== undefined || busy) return;
    const next = { ...answers, [question.id]: optionIndex };
    setAnswers(next);
    try {
      const { data } = await api.post(`${base}/${attemptRef.current}/answer`, { question_id: question.id, value: optionIndex });
      if (data.finished) await finish(next);
    } catch (err) {
      setError(errMsg(err));
    }
  };

  const startFinal = () => {
    if (strict) goFullscreen();   // foydalanuvchi bosishi bilan (brauzer talabi)
    begin(strict);
  };

  const questions = attempt?.questions || [];
  const answered = Object.keys(answers).length;
  const q = questions[cur];
  const title = final ? t('vx.finalTitle') : t('vx.title', { n: unit.unit_number });

  // Javob tanlangach (test kabi) keyingi savolga o'tadi
  const pick = async (question, optionIndex) => {
    await choose(question, optionIndex);
    if (cur < questions.length - 1) setTimeout(() => setCur(c => Math.min(c + 1, questions.length - 1)), 350);
  };

  const body = (
    <div className="vx-overlay" ref={root}>
      <div className="vx-top">
        <strong>{title}</strong>
        {phase === 'exam' && <span className="badge">{answered} / {questions.length}</span>}
        {(phase === 'error' || phase === 'result' || phase === 'intro') && (
          <button className="btn btn-ghost btn-sm" onClick={() => { if (phase === 'result') onFinished?.(); onClose(); }}>{t('common.close')}</button>
        )}
      </div>
      <div className="vx-main test-shell">
        {phase === 'intro' && (
          <div className="card stack">
            <h2>{t('vx.finalTitle')}</h2>
            <p className="text-2">{t('vx.finalInfo')}</p>
            <label className="row" style={{ gap: 10, alignItems: 'flex-start', cursor: 'pointer' }}>
              <input type="checkbox" checked={strict} onChange={e => setStrict(e.target.checked)} style={{ marginTop: 4 }} />
              <span><strong>{t('vx.strictOpt')}</strong><br /><span className="hint">{t('vx.strictHint')}</span></span>
            </label>
            <button className="btn btn-primary" onClick={startFinal}>{t('vx.start')}</button>
          </div>
        )}
        {phase === 'starting' && <div className="card" style={{ textAlign: 'center' }}><Spinner size={34} /><p>{t('vx.starting')}</p></div>}
        {phase === 'error' && <div className="card stack">
          <div className="alert alert-danger">{error}</div>
          <button className="btn btn-primary" onClick={() => (final ? setPhase('intro') : begin())}>{t('vx.retry')}</button>
        </div>}
        {phase === 'exam' && q && (
          <>
            <div className="row-between">
              <div><h2>{title}</h2><span className="hint">{t('vx.choose')}</span></div>
              {!strictRef.current && !document.fullscreenElement && <button type="button" className="btn btn-ghost btn-sm" onClick={goFullscreen}>⛶ Full screen</button>}
            </div>
            <div className="row" style={{ flexWrap: 'nowrap' }}>
              <div className="progress spacer"><span style={{ width: `${(answered / questions.length) * 100}%` }} /></div>
              <span className="mono muted">{answered}/{questions.length}</span>
            </div>
            <div className="card q-card anim-scale-in" key={q.id}>
              <span className="badge badge-primary" style={{ marginBottom: 12 }}>
                {q.practice ? t('vx.practice') : t('test.question')} {cur + 1} / {questions.length}
              </span>
              {q.practice && <p className="hint">{t('vx.practicePrompt')}</p>}
              <div className="q-text row" style={{ justifyContent: 'center', gap: 10 }}>
                <span className="vx-word-big">{q.display_word || q.word}</span>
                {!q.practice && <Speak text={q.word} lang="en" />}
              </div>
              {q.options.map((option, i) => (
                <button key={i} type="button" disabled={answers[q.id] !== undefined}
                  className={`opt ${answers[q.id] === i ? 'picked' : ''}`} onClick={() => pick(q, i)}>
                  <span className="opt-letter">{String.fromCharCode(65 + i)}</span><span>{option}</span>
                </button>
              ))}
              {error && <div className="alert alert-danger">{error}</div>}
              <div className="row-between" style={{ marginTop: 18 }}>
                <button className="btn btn-ghost" disabled={cur === 0} onClick={() => setCur(c => c - 1)}>← {t('common.back')}</button>
                {cur < questions.length - 1
                  ? <button className="btn btn-primary" onClick={() => setCur(c => c + 1)}>{t('common.next')} →</button>
                  : <button className="btn btn-primary" disabled={busy || answered < questions.length} onClick={() => finish(answers)}>
                    {busy ? <Spinner size={16} /> : <CheckCircle2 size={16} />} {t('vx.finish')}
                  </button>}
              </div>
            </div>
            <div className="card">
              <div className="row-between" style={{ marginBottom: 12 }}>
                <strong>{t('test.palette')}</strong>
                <button className="btn btn-sm btn-primary" disabled={busy || answered < questions.length} onClick={() => finish(answers)}>
                  <CheckCircle2 size={14} /> {t('vx.finish')}
                </button>
              </div>
              <div className="palette">{questions.map((x, i) => (
                <button key={x.id} className={`pal ${answers[x.id] !== undefined ? 'done' : ''} ${i === cur ? 'cur' : ''}`} onClick={() => setCur(i)}>{i + 1}</button>
              ))}</div>
            </div>
          </>
        )}
        {phase === 'result' && result && (
          <div className="card stack" style={{ textAlign: 'center' }}>
            {result.stopped ? <OctagonX size={54} color="var(--danger)" style={{ alignSelf: 'center' }} />
              : result.passed ? <CheckCircle2 size={54} color="var(--success)" style={{ alignSelf: 'center' }} /> : <XCircle size={54} color="var(--danger)" style={{ alignSelf: 'center' }} />}
            <h2>{result.stopped ? t(final ? 'vx.stoppedFinal' : 'vx.stopped') : result.passed ? t('vx.passed') : t('vx.failed')}</h2>
            <p className="text-2">{result.found?.length ?? 0} / {(result.found?.length ?? 0) + (result.missed?.length ?? 0)} · {result.percent}%</p>
            {result.passed ? <p className="badge badge-success" style={{ alignSelf: 'center' }}>+{result.score} {t('vx.points')}</p>
              : <p className="hint">{t('vx.noPoints')}</p>}
            {result.missed?.length > 0 && (
              <div style={{ textAlign: 'left' }}>
                <strong>{t('vx.missed')}</strong>
                <table className="vx-words"><tbody>{result.missed.map((missed, i) => <tr key={i}>
                  <td>{missed.en} {missed.practice && <span className="badge">{t('vx.practice')}</span>}</td><td>{missed.uz}</td>
                </tr>)}</tbody></table>
              </div>
            )}
          </div>
        )}
      </div>
      {warn > 0 && (
        <div className="vx-warn"><div>
          <ShieldAlert size={44} color="var(--warning, #f97316)" />
          <h2>{t('vx.warnTitleFree', { n: warn })}</h2>
          <p className="text-2">{t('vx.warnText')}</p>
          <button className="btn btn-primary" onClick={closeWarn}>{t('vx.continue')}</button>
        </div></div>
      )}
    </div>
  );
  // Portal: sahifa konteynerlaridagi animatsiya/transform "fixed" ni cheklab qo'ymasin
  return createPortal(body, document.body);
}
