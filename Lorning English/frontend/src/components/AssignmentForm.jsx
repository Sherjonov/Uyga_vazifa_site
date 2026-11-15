import FileDrop from './FileDrop';
import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { CheckCheck, Plus, Trash2, Users } from 'lucide-react';
import GroupSelect from './GroupSelect';
import { Empty, SkeletonList, Spinner } from './Loader';
import useGroups from '../utils/useGroups';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';
import { fmtDateTime, localToIso } from '../utils/format';

/** Uyga vazifa yoki darsdan tashqari topshiriq qo'shish va mavjudlarini boshqarish. */
export default function AssignmentForm({ kind }) {
  const { t, lang } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [f, setF] = useState({ title: '', description: '', due: '', max: 10 });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState(null);
  const isExtra = kind === 'extra';

  const load = useCallback(() => {
    if (!groupId) return setItems([]);
    api.get('/assignments', { params: { group_id: groupId, kind } }).then(r => setItems(r.data)).catch(() => setItems([]));
  }, [groupId, kind]);
  useEffect(() => { if (!gl) { setItems(null); load(); } }, [gl, load]);

  const submit = async e => {
    e.preventDefault();
    if (!groupId || !f.title.trim()) return toast.error(t('err.fillAll'));
    if (!isExtra && !f.due) return toast.error(t('assign.dueRequired'));
    const fd = new FormData();
    fd.append('group_id', groupId); fd.append('kind', kind); fd.append('title', f.title.trim());
    fd.append('description', f.description); fd.append('max_score', f.max);
    if (f.due) fd.append('due_at', localToIso(f.due));
    if (file) fd.append('file', file);
    setBusy(true);
    try {
      await api.post('/assignments', fd);
      toast.success(t('common.saved'));
      setF({ title: '', description: '', due: '', max: 10 }); setFile(null); e.target.reset(); load();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  const remove = async a => {
    if (!window.confirm(t('common.confirmDelete'))) return;
    try { await api.delete(`/assignments/${a.id}`); load(); } catch (err) { toast.error(errMsg(err)); }
  };

  if (!gl && groups.length === 0) return <div className="card"><Empty icon={Users} title={t('groups.none')} text={t('groups.noneText')} action={<Link to="/teacher/students" className="btn btn-primary">{t('groups.create')}</Link>} /></div>;

  return (
    <div className="grid grid-2" style={{ alignItems: 'start' }}>
      <form className="card" onSubmit={submit}>
        <div className="card-title"><h3>{isExtra ? t('extra.new') : t('assign.newHomework')}</h3></div>
        <div className="field"><label>{t('groups.group')}</label><GroupSelect groups={groups} value={groupId} onChange={setGroupId} /></div>
        <div className="field"><label>{t('assign.title')}</label><input className="input" value={f.title} onChange={e => setF({ ...f, title: e.target.value })} maxLength={200} /></div>
        <div className="field"><label>{t('assign.description')}</label><textarea className="textarea" value={f.description} onChange={e => setF({ ...f, description: e.target.value })} /></div>
        <div className="grid grid-2" style={{ gap: 12 }}>
          {!isExtra && <div className="field"><label>{t('assign.due')}</label><input className="input" type="datetime-local" value={f.due} onChange={e => setF({ ...f, due: e.target.value })} /></div>}
          <div className="field"><label>{t('assign.maxScore')}</label><input className="input" type="number" min={1} max={1000} value={f.max} onChange={e => setF({ ...f, max: e.target.value })} /></div>
        </div>
        <div className="field"><label>{t('assign.file')}</label><FileDrop file={file} onChange={setFile} accept="*/*" label={t('assign.file')} hint="PDF, DOC, IMG…" /></div>
        <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner size={16} /> : <Plus size={16} />} {t('common.add')}</button>
      </form>
      <div className="stack">
        <h3>{t('assign.existing')}</h3>
        {items === null ? <SkeletonList n={3} h={100} /> : items.length === 0 ? <div className="card"><Empty title={t('assign.none')} /></div> : items.map(a => (
          <div key={a.id} className="card stack" style={{ gap: 10 }}>
            <div className="row-between"><strong>{a.title}</strong><button className="btn btn-danger btn-icon btn-sm" onClick={() => remove(a)} aria-label="delete"><Trash2 size={15} /></button></div>
            <div className="assign-meta row">
              {a.due_at && <span className="badge">{fmtDateTime(a.due_at, lang)}</span>}
              <span className="badge badge-success">{a.submitted_count}/{a.members_count} {t('assign.submittedShort')}</span>
              {a.reviewed_count < a.submitted_count && <span className="badge badge-warning">{a.submitted_count - a.reviewed_count} {t('assign.toReview')}</span>}
            </div>
            <Link to={`/teacher/review?a=${a.id}`} className="btn btn-ghost btn-sm" style={{ alignSelf: 'flex-start' }}><CheckCheck size={15} /> {t('nav.review')}</Link>
          </div>
        ))}
      </div>
    </div>
  );
}
