import { Link } from 'react-router-dom';
import FileChips from './FileChips';
import { useLang } from '../context/LangContext';
import { fmtDuration, fmtShort } from '../utils/format';
import './work.css';

/** Uyga vazifa kartasi. mode: pending (topshirilmagan) | checking (tekshirilmoqda) | graded (baholangan) */
export default function HwCard({ a, mode, onSubmit }) {
  const { t, lang } = useLang();
  const sub = a.submission;
  const left = a.due_at ? (new Date(a.due_at) - Date.now()) / 1000 : null;
  const ctx = [a.group_name, fmtShort(a.created_at, lang)].filter(Boolean).join(' · ');

  let pill;
  if (mode === 'graded') pill = <span className="wk-pill wk-pill--ok">✅ {sub.score}/{a.max_score}</span>;
  else if (mode === 'checking') pill = <span className="wk-pill">{t('wk.checking')}</span>;
  else if (a.overdue) pill = <span className="wk-pill wk-pill--bad">{t('assign.overdue')}</span>;
  else pill = <span className="wk-pill wk-pill--new">{t('wk.new')}</span>;

  return (
    <article className="wk-card">
      <header className="wk-head">
        <div>
          {ctx && <div className="wk-ctx">{ctx}</div>}
          <h3 className="wk-title">{a.title}</h3>
        </div>
        {pill}
      </header>

      <div className="wk-chips">
        <span className="wk-chip">{t('assign.max', { n: a.max_score })}</span>
        {a.due_at && <span className="wk-chip">⏰ {fmtShort(a.due_at, lang)}</span>}
        {mode === 'pending' && left != null && left > 0 && <span className="wk-chip wk-chip--hot">⏳ {t('assign.left')}: {fmtDuration(left, t)}</span>}
      </div>

      {a.description && (
        <details className="wk-detail">
          <summary>📋 {t('assign.text')}</summary>
          <p>{a.description}</p>
        </details>
      )}
      {a.file_url && <FileChips urls={[a.file_url]} />}
      <Link to={`/student/uztoz-ai?a=${a.id}`} className="wk-ask">🧑‍🏫 {t('assign.askAi')}</Link>

      {sub && (
        <div className="wk-sub">
          <div className="wk-sub-head">
            📤 {t('wk.submittedAt', { d: fmtShort(sub.submitted_at, lang) })}
            {sub.is_late && <small>· {t('assign.wasLate')}</small>}
            {a.resubmits > 0 && <small>· {t('assign.resubmitted', { n: a.resubmits })}</small>}
          </div>
          {sub.text && <pre className="wk-code">{sub.text}</pre>}
          <FileChips urls={sub.files || []} />
          {mode === 'graded' && sub.comment && <div className="wk-comment">💬 <strong>{t('assign.teacherComment')}:</strong> {sub.comment}</div>}
        </div>
      )}

      {mode === 'pending' ? (
        <>
          {a.overdue && a.late_penalty > 0 && <p className="hint" style={{ margin: 0 }}>⚠️ {t('assign.lateNote', { n: a.late_penalty })}</p>}
          <button className="wk-btn wk-btn--primary" onClick={() => onSubmit(a)}>
            📤 {a.overdue ? t('assign.submitLate', { n: a.late_penalty || 0 }) : t('assign.submit')}
          </button>
        </>
      ) : a.can_edit && (
        <button className="wk-btn" onClick={() => onSubmit(a)}>🔁 {t('wk.resubmit', { n: a.resubmit_penalty })}</button>
      )}
    </article>
  );
}
