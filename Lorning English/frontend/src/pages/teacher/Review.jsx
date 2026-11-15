import { useCallback, useEffect, useMemo, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { CheckCheck } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import FileChips from '../../components/FileChips';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtShort, initials } from '../../utils/format';
import '../../components/work.css';
import './teacher.css';

/** AI va matn o'xshashligi taxminiy tahlil; yakuniy qaror o'qituvchida. */
function AiPanel({ ai, similarity }) {
  const { t, lang } = useLang();
  return (
    <section className="wk-analysis" aria-label={t('review.analysisTitle')}>
      <header className="wk-analysis-head">
        <div><span className="wk-analysis-icon">✦</span><strong>{t('review.analysisTitle')}</strong></div>
        <span className="wk-analysis-badge">{t('review.analysisEstimate')}</span>
      </header>
      {ai && (
        <div className={`wk-ai-result wk-ai-result--${ai.assessment}`}>
          <div className="wk-ai-title">
            <strong>🤖 {t(`review.ai.${ai.assessment}`)}</strong>
            <span>{t('review.aiConfidence')}: {ai.confidence}%</span>
          </div>
          <div className="wk-ai-bar" role="progressbar" aria-valuenow={ai.confidence} aria-valuemin={0} aria-valuemax={100}>
            <i style={{ width: `${ai.confidence}%` }} />
          </div>
          {ai.indicators?.length
            ? <ul>{ai.indicators.map((x, i) => <li key={i}>{x}</li>)}</ul>
            : <p className="hint">{t('review.ai.noIndicators')}</p>}
          <p className="hint">{t('review.aiNotice')}{ai.checked_at ? ` · ${fmtShort(ai.checked_at, lang)}` : ''}</p>
        </div>
      )}
      {similarity && (
        <div className="wk-similarity">
          <div className="wk-similarity-head">
            <strong>🔗 {t('review.similarityTitle')}</strong>
            <span>{similarity.matches.length
              ? t('review.similarityCount', { n: similarity.matches.length })
              : t('review.similarityNone')}</span>
          </div>
          {similarity.matches.length > 0 && (
            <ul className="wk-similarity-list">
              {similarity.matches.map(match => (
                <li key={match.student_id}>
                  <span>{t('review.similarityWith', { name: match.student_name })}</span>
                  <strong>{match.percent}%</strong>
                  {match.basis === 'code_structure' && <small>{t('review.similarityCode')}</small>}
                  <div className="wk-similarity-bar" role="progressbar" aria-valuenow={match.percent} aria-valuemin={0} aria-valuemax={100}>
                    <i style={{ width: `${match.percent}%` }} />
                  </div>
                </li>
              ))}
            </ul>
          )}
          <p className="hint">{t('review.similarityNotice')}{similarity.checked_at ? ` · ${fmtShort(similarity.checked_at, lang)}` : ''}</p>
        </div>
      )}
    </section>
  );
}

/** O'quvchi shu vazifa bo'yicha Ustoz AI dan nimalar deb so'ragani */
function AiQuestions({ assignmentId, studentId }) {
  const { t, lang } = useLang();
  const [items, setItems] = useState(null);
  useEffect(() => { api.get('/ai/logs', { params: { assignment_id: assignmentId, student_id: studentId } }).then(r => setItems(r.data)).catch(() => setItems([])); }, [assignmentId, studentId]);
  if (items === null) return null;
  return (
    <details className="wk-detail">
      <summary>🧑‍🏫 {t('review.aiQuestions')} ({items.length})</summary>
      {items.length === 0 ? <p className="hint">{t('review.aiQuestionsNone')}</p> : (
        <ul style={{ paddingLeft: 18, margin: '8px 0' }}>{items.map(q => <li key={q.id} style={{ marginBottom: 6 }}>{q.question} <small className="hint">· {fmtShort(q.created_at, lang)}</small></li>)}</ul>
      )}
    </details>
  );
}

function ReviewCard({ item, assignment, onSaved, threshold = 70 }) {
  const { t, lang } = useLang();
  const toast = useToast();
  const sub = item.submission;
  const max = assignment.max_score;
  const [score, setScore] = useState(sub?.score ?? '');
  const [comment, setComment] = useState(sub?.comment || '');
  const [ai, setAi] = useState(sub?.ai || null);
  const [similarity, setSimilarity] = useState(sub?.similarity || null);
  const [busy, setBusy] = useState(false);
  const [aiBusy, setAiBusy] = useState(false);
  const [confirmedAnalysis, setConfirmedAnalysis] = useState(false);
  const graded = sub?.score != null;
  const hasContent = !!(sub?.text || (sub?.files || []).length);
  const needsAnalysisConfirmation = ai?.assessment === 'likely_ai' || (similarity?.matches || []).some(match => match.percent >= threshold);

  const check = async () => {
    setAiBusy(true);
    const errors = [];
    try {
      try {
        const { data } = await api.post(`/assignments/submissions/${sub.id}/similarity-check`);
        setSimilarity(data);
      } catch (err) { errors.push(errMsg(err)); }
      try {
        const { data } = await api.post(`/assignments/submissions/${sub.id}/ai-check`);
        setAi(data);
      } catch (err) { errors.push(errMsg(err)); }
      setConfirmedAnalysis(false);
    } finally {
      setAiBusy(false);
    }
    if (errors.length) toast.error(errors.join(' · '));
  };
  const save = async () => {
    if (score === '') return toast.error(t('review.scoreRequired'));
    if (needsAnalysisConfirmation && !confirmedAnalysis) return toast.error(t('review.confirmAnalysisRequired'));
    setBusy(true);
    try {
      await api.put(`/assignments/submissions/${sub.id}/review`, {
        score: Number(score), comment, analysis_confirmed: confirmedAnalysis
      });
      toast.success(t('review.saved'));
      onSaved();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  const quick = f => setScore(String(Math.round(max * f * 2) / 2));

  let pill;
  if (!item.submitted) pill = <span className="wk-pill wk-pill--bad">{t('review.missing')}</span>;
  else if (graded) pill = <span className="wk-pill wk-pill--ok">✅ {sub.score}/{max}</span>;
  else pill = <span className="wk-pill">{t('wk.checking')}</span>;

  return (
    <article className="wk-card">
      <header className="wk-head">
        <div className="wk-who">
          <span className="avatar">{initials(item.student.name)}</span>
          <div>
            <div className="wk-ctx">{[assignment.group_name, item.submitted && fmtShort(sub.submitted_at, lang)].filter(Boolean).join(' · ')}</div>
            <strong className="wk-name">{item.student.name}</strong>
          </div>
        </div>
        {pill}
      </header>

      <div className="wk-chips">
        <span className="wk-chip">{t('assign.max', { n: max })}</span>
        {assignment.due_at && <span className="wk-chip">⏰ {fmtShort(assignment.due_at, lang)}</span>}
        {sub?.is_late && <span className="wk-chip wk-chip--hot">⏰ {t('assign.wasLate')}</span>}
        {item.resubmits > 0 && <span className="wk-chip wk-chip--hot">🔁 {t('assign.resubmitted', { n: item.resubmits })}</span>}
      </div>

      <AiQuestions assignmentId={assignment.id} studentId={item.student.id} />

      {!item.submitted ? <p className="muted" style={{ margin: 0 }}>{t('review.missingText')}</p> : (
        <>
          <div className="wk-sub">
            <div className="wk-sub-head">📤 {t('wk.submittedAt', { d: fmtShort(sub.submitted_at, lang) })}</div>
            {sub.text ? <pre className="wk-code">{sub.text}</pre> : !(sub.files || []).length && <span className="muted">—</span>}
            <FileChips urls={sub.files || []} />
          </div>

          {(ai || similarity) && <AiPanel ai={ai} similarity={similarity} />}
          {needsAnalysisConfirmation && (
            <label className="wk-analysis-confirm">
              <input type="checkbox" checked={confirmedAnalysis} onChange={event => setConfirmedAnalysis(event.target.checked)} />
              <span>{t('review.confirmAnalysis')}</span>
            </label>
          )}

          <div className="wk-grade">
            <div className="wk-score-row">
              <input className="wk-score-input" type="number" min={0} max={max} step="0.5" value={score}
                onChange={e => setScore(e.target.value)} placeholder="0" aria-label={t('review.scoreLabel')} />
              <span className="wk-max">/ {max}</span>
              <div className="wk-quick">
                {[0, 0.5, 0.75, 1].map(f => <button key={f} type="button" className="wk-q" onClick={() => quick(f)}>{Math.round(max * f * 2) / 2}</button>)}
              </div>
            </div>
            <textarea className="wk-comment-input" value={comment} onChange={e => setComment(e.target.value)} placeholder={t('review.commentPh')} />
            <div className="wk-quick">
              {['ai', 'good', 'redo'].map(k => <button key={k} type="button" className="wk-q" onClick={() => setComment(t(`review.quick.${k}`))}>{t(`review.quick.${k}`)}</button>)}
            </div>
          </div>

          <div className="wk-actions">
            <button className={`wk-btn ${!ai && hasContent ? 'wk-btn--primary' : ''}`} onClick={check} disabled={aiBusy || !hasContent}
              title={hasContent ? t('review.checkHint') : t('review.noContentAi')}>
              {aiBusy ? <Spinner size={16} /> : '🔍'} {aiBusy ? t('review.aiChecking') : ai || similarity ? t('review.recheck') : t('review.check')}
            </button>
            <button className={`wk-btn ${ai || !hasContent ? 'wk-btn--primary' : ''}`} onClick={save} disabled={busy}>
              {busy ? <Spinner size={16} /> : '💾'} {graded ? t('review.update') : t('review.grade')}
            </button>
          </div>
          <p className="hint" style={{ margin: 0 }}>{hasContent ? t('review.checkHint') : t('review.noContentAi')} · {t('review.notifyHint')}</p>
        </>
      )}
    </article>
  );
}

export default function Review() {
  const { t } = useLang();
  const [params, setParams] = useSearchParams();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [list, setList] = useState(null);
  const [aid, setAid] = useState(Number(params.get('a')) || null);
  const [detail, setDetail] = useState(null);
  const [tab, setTab] = useState(null);
  const [threshold, setThreshold] = useState(70);
  useEffect(() => { api.get('/settings/teacher').then(r => setThreshold(r.data.similarity_threshold || 70)).catch(() => {}); }, []);

  useEffect(() => {
    if (gl) return;
    setList(null);
    api.get('/assignments', { params: groupId ? { group_id: groupId } : {} }).then(r => { setList(r.data); }).catch(() => setList([]));
  }, [gl, groupId]);

  // havoladan kelgan vazifaning guruhini avtomatik tanlash
  useEffect(() => {
    const a = Number(params.get('a'));
    if (a && list && !list.some(x => x.id === a)) api.get(`/assignments/${a}`).then(r => setGroupId(r.data.group_id)).catch(() => {});
  }, [params, list]); // eslint-disable-line react-hooks/exhaustive-deps

  const loadDetail = useCallback(() => {
    if (!aid) return setDetail(null);
    api.get(`/assignments/${aid}/submissions`).then(r => setDetail(r.data)).catch(() => setDetail(null));
  }, [aid]);
  useEffect(() => { setTab(null); loadDetail(); }, [loadDetail]);

  const groupsOf = useMemo(() => {
    const items = detail?.items || [];
    return {
      todo: items.filter(i => i.submitted && i.submission.score == null),
      done: items.filter(i => i.submitted && i.submission.score != null),
      missing: items.filter(i => !i.submitted),
    };
  }, [detail]);
  const active = tab || (groupsOf.todo.length ? 'todo' : groupsOf.done.length ? 'done' : groupsOf.missing.length ? 'missing' : 'todo');
  const shown = groupsOf[active] || [];

  const pick = id => { setAid(id); setParams(id ? { a: id } : {}); };

  return (
    <div className="page">
      <PageHeader icon={CheckCheck} title={t('nav.review')} subtitle={t('review.subtitle')} />
      <div className="row" style={{ marginBottom: 18 }}>
        <GroupSelect groups={groups} value={groupId} onChange={id => { setGroupId(id); pick(null); }} />
        <select className="select" style={{ width: 'auto', minWidth: 260 }} value={aid || ''} onChange={e => pick(Number(e.target.value) || null)}>
          <option value="">{t('review.pick')}</option>
          {(list || []).map(a => <option key={a.id} value={a.id}>{a.kind === 'task' ? '⏱ ' : a.kind === 'extra' ? '✨ ' : '📘 '}{a.title} ({a.submitted_count}/{a.members_count})</option>)}
        </select>
      </div>

      {!aid ? <div className="card"><Empty icon={CheckCheck} title={t('review.pickTitle')} /></div> : !detail ? <SkeletonList n={2} h={300} /> : (
        <>
          <div className="wk-tabs">
            <button className={`wk-tab ${active === 'todo' ? 'active' : ''}`} onClick={() => setTab('todo')}>📥 {t('review.tabTodo')} ({groupsOf.todo.length})</button>
            <button className={`wk-tab ${active === 'done' ? 'active' : ''}`} onClick={() => setTab('done')}>✅ {t('review.tabDone')} ({groupsOf.done.length})</button>
            <button className={`wk-tab ${active === 'missing' ? 'active' : ''}`} onClick={() => setTab('missing')}>❌ {t('review.tabMissing')} ({groupsOf.missing.length})</button>
          </div>
          {shown.length === 0 ? <div className="card"><Empty icon={CheckCheck} title={t('review.emptyTab')} /></div> : (
            <div className="wk-list stagger">
              {shown.map(it => <ReviewCard key={`${aid}-${it.student.id}-${it.submission?.submitted_at || 0}-${it.submission?.score ?? 'n'}`} item={it} assignment={detail.assignment} onSaved={loadDetail} threshold={threshold} />)}
            </div>
          )}
        </>
      )}
    </div>
  );
}
