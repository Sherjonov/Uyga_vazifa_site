import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Eye, Presentation, Trash2, UploadCloud, Users } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import Modal from '../../components/Modal';
import SlideDeck from '../../components/SlideDeck';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDate } from '../../utils/format';
import './teacher.css';

export default function AddLesson() {
  const { t, lang } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [title, setTitle] = useState('');
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [items, setItems] = useState(null);
  const [preview, setPreview] = useState(null);
  const [over, setOver] = useState(false);
  const input = useRef(null);

  const load = useCallback(() => {
    if (!groupId) return setItems([]);
    api.get('/lessons', { params: { group_id: groupId } }).then(r => setItems(r.data)).catch(() => setItems([]));
  }, [groupId]);
  useEffect(() => { if (!gl) { setItems(null); load(); } }, [gl, load]);

  const submit = async e => {
    e.preventDefault();
    if (!groupId || !title.trim() || !file) return toast.error(t('err.fillAll'));
    const fd = new FormData();
    fd.append('group_id', groupId); fd.append('title', title.trim()); fd.append('file', file);
    setBusy(true);
    try { await api.post('/lessons', fd); toast.success(t('lessons.created')); setTitle(''); setFile(null); load(); } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  const open = async l => { try { const { data } = await api.get(`/lessons/${l.id}`); setPreview(data); } catch (err) { toast.error(errMsg(err)); } };
  const remove = async l => { if (!window.confirm(t('common.confirmDelete'))) return; try { await api.delete(`/lessons/${l.id}`); load(); } catch (err) { toast.error(errMsg(err)); } };

  if (!gl && groups.length === 0) return <div className="page"><div className="card"><Empty icon={Users} title={t('groups.none')} text={t('groups.noneText')} action={<Link to="/teacher/students" className="btn btn-primary">{t('groups.create')}</Link>} /></div></div>;

  return (
    <div className="page">
      <PageHeader icon={Presentation} title={t('nav.addLesson')} subtitle={t('lessons.addSub')} />
      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <form className="card" onSubmit={submit}>
          <div className="field"><label>{t('groups.group')}</label><GroupSelect groups={groups} value={groupId} onChange={setGroupId} /></div>
          <div className="field"><label>{t('lessons.title')}</label><input className="input" value={title} onChange={e => setTitle(e.target.value)} maxLength={200} /></div>
          <div className={`drop ${over ? 'over' : ''}`} onClick={() => input.current?.click()} onDragOver={e => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
            onDrop={e => { e.preventDefault(); setOver(false); const f = e.dataTransfer.files[0]; if (f) setFile(f); }}>
            <UploadCloud size={34} /><strong>{file ? file.name : t('lessons.dropPdf')}</strong><span className="hint">{t('lessons.pdfHint')}</span>
            <input ref={input} type="file" accept="application/pdf,.pdf" hidden onChange={e => setFile(e.target.files[0] || null)} />
          </div>
          <button className="btn btn-primary" disabled={busy} style={{ marginTop: 16 }}>{busy ? <><Spinner size={16} /> {t('lessons.converting')}</> : <><UploadCloud size={16} /> {t('common.upload')}</>}</button>
        </form>
        <div className="stack">
          <h3>{t('lessons.existing')}</h3>
          {items === null ? <SkeletonList n={3} h={80} /> : items.length === 0 ? <div className="card"><Empty icon={Presentation} title={t('lessons.empty')} /></div> : items.map(l => (
            <div key={l.id} className="list-item">
              <div className="lesson-ico" style={{ width: 46, height: 46, borderRadius: 14 }}><Presentation size={22} /></div>
              <div className="spacer"><strong>{l.title}</strong><div className="hint">{l.page_count} {t('lessons.slides')} · {fmtDate(l.created_at, lang)}</div></div>
              <button className="btn btn-ghost btn-icon btn-sm" onClick={() => open(l)}><Eye size={16} /></button>
              <button className="btn btn-danger btn-icon btn-sm" onClick={() => remove(l)}><Trash2 size={16} /></button>
            </div>
          ))}
        </div>
      </div>
      <Modal open={!!preview} onClose={() => setPreview(null)} title={preview?.title} size="xl">{preview && <SlideDeck slides={preview.slides} title={preview.title} />}</Modal>
    </div>
  );
}
