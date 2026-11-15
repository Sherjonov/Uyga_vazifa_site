import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpen, Eye, ListChecks, Lock, RefreshCw, Trash2, Unlock, UploadCloud, Users } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import Modal from '../../components/Modal';
import BookViewer from '../../components/BookViewer';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import '../../styles/extra.css';

const toText = words => (words || []).map(w => `${w.en} - ${w.uz}`).join('\n');
const fromText = text => text.split('\n').map(l => l.split(/\s+[-–—=]\s+|\t/)).filter(p => p.length >= 2 && p[0].trim() && p[1].trim()).map(p => ({ en: p[0].trim(), uz: p.slice(1).join(' - ').trim() }));

/** Kitoblar: Dars kitobi va Lug'at kitobi (PDF yuklash, ko'rish, unitlarni tuzatish) */
export default function Books() {
  const { t } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [type, setType] = useState('lesson');
  const [books, setBooks] = useState(null);
  const [title, setTitle] = useState('');
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [view, setView] = useState(null);
  const [units, setUnits] = useState(null); // {book, items}
  const input = useRef(null);

  const load = useCallback(() => {
    if (!groupId) return setBooks([]);
    api.get('/books', { params: { group_id: groupId, type } }).then(r => setBooks(r.data)).catch(() => setBooks([]));
  }, [groupId, type]);
  useEffect(() => { if (!gl) { setBooks(null); load(); } }, [gl, load]);

  const upload = async e => {
    e.preventDefault();
    if (!groupId || !title.trim() || !file) return toast.error(t('err.fillAll'));
    const fd = new FormData();
    fd.append('type', type); fd.append('title', title.trim()); fd.append('group_id', groupId); fd.append('file', file);
    setBusy(true);
    try {
      const { data } = await api.post('/books', fd, { timeout: 180000 });
      toast.success(type === 'vocab' ? t('book.vocabParsed', { n: data.units_count }) : t('common.saved'));
      setTitle(''); setFile(null); if (input.current) input.current.value = ''; load();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  const reparse = async b => {
    if (!window.confirm(t('book.reparseConfirm'))) return;
    setBusy(true);
    try {
      const { data } = await api.post(`/books/${b.id}/reparse`, null, { timeout: 180000 });
      toast.success(t('book.reparsed', { n: data.units_count, w: data.words_count })); load();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  const remove = async b => { if (!window.confirm(t('common.confirmDelete'))) return; try { await api.delete(`/books/${b.id}`); load(); } catch (err) { toast.error(errMsg(err)); } };
  const openUnits = async b => { try { const { data } = await api.get(`/books/${b.id}/units`); setUnits({ book: b, items: data.map(u => ({ ...u, text: toText(u.words) })) }); } catch (err) { toast.error(errMsg(err)); } };
  const saveUnit = async u => {
    const words = fromText(u.text);
    if (!words.length) return toast.error(t('book.noWords'));
    try { await api.put(`/books/${units.book.id}/units/${u.id}`, { title: u.title || '', words }); toast.success(t('common.saved')); } catch (err) { toast.error(errMsg(err)); }
  };
  const setUnitAccess = async u => {
    try {
      const { data } = await api.put(`/books/${units.book.id}/units/${u.id}/access`, { open: !u.open_for_students });
      setUnits(current => current && ({
        ...current,
        items: current.items.map(item => item.id === u.id
          ? { ...item, open_for_students: data.open_for_students }
          : item)
      }));
      toast.success(t(data.open_for_students ? 'book.unitOpened' : 'book.unitLocked'));
    } catch (err) { toast.error(errMsg(err)); }
  };

  if (!gl && groups.length === 0) return <div className="page"><div className="card"><Empty icon={Users} title={t('groups.none')} text={t('groups.noneText')} action={<Link to="/teacher/students" className="btn btn-primary">{t('groups.create')}</Link>} /></div></div>;

  return (
    <div className="page page-wide">
      <PageHeader icon={BookOpen} title={t('nav.books')} subtitle={t('book.subtitle')} />
      {view ? (
        <div className="stack"><button className="btn btn-ghost" style={{ alignSelf: 'flex-start' }} onClick={() => setView(null)}>← {t('common.back')}</button><BookViewer url={view.pdf_url} title={view.title} /></div>
      ) : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="row">
            <GroupSelect groups={groups} value={groupId} onChange={setGroupId} />
            <div className="tabs"><button className={`tab ${type === 'lesson' ? 'active' : ''}`} onClick={() => setType('lesson')}>{t('book.lesson')}</button>
              <button className={`tab ${type === 'vocab' ? 'active' : ''}`} onClick={() => setType('vocab')}>{t('book.vocab')}</button></div>
          </div>
          <div className="grid grid-2" style={{ alignItems: 'start' }}>
            <form className="card stack" onSubmit={upload}>
              <h3>{type === 'lesson' ? t('book.uploadLesson') : t('book.uploadVocab')}</h3>
              <div className="field"><label>{t('assign.title')}</label><input className="input" value={title} maxLength={200} onChange={e => setTitle(e.target.value)} /></div>
              <div className="field"><label>PDF</label><input ref={input} className="input" type="file" accept="application/pdf,.pdf" onChange={e => setFile(e.target.files[0] || null)} /></div>
              {type === 'vocab' && <p className="hint">{t('book.vocabHint')}</p>}
              <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner size={16} /> : <UploadCloud size={16} />} {t('common.upload')}</button>
            </form>
            <div className="stack">
              {books === null ? <SkeletonList n={2} h={80} /> : books.length === 0 ? <div className="card"><Empty icon={BookOpen} title={t('book.none')} /></div> : books.map(b => (
                <div key={b.id} className="card row-between">
                  <div><strong>{b.title}</strong><div className="row" style={{ gap: 6, marginTop: 6 }}>
                    <span className="badge">{b.page_count} {t('book.pages')}</span>{(b.type === 'vocab' || b.units_count > 0) && <span className="badge badge-info">{b.units_count} unit</span>}</div></div>
                  <div className="row">
                    {(b.type === 'vocab' || b.units_count > 0) && <button className="btn btn-ghost btn-sm" onClick={() => openUnits(b)}><ListChecks size={15} /> {t('book.units')}</button>}
                    {(b.type === 'vocab' || b.units_count > 0) && <button className="btn btn-ghost btn-icon btn-sm" disabled={busy} title={t('book.reparse')} onClick={() => reparse(b)}><RefreshCw size={15} /></button>}
                    <button className="btn btn-ghost btn-sm" onClick={() => setView(b)}><Eye size={15} /> {t('book.open')}</button>
                    <button className="btn btn-danger btn-icon btn-sm" onClick={() => remove(b)}><Trash2 size={15} /></button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
      <Modal open={!!units} onClose={() => setUnits(null)} size="lg" title={units ? `${units.book.title} — ${t('book.units')}` : ''}>
        {units && <div className="stack">
          <p className="hint">{t('book.editHint')}</p>
          {units.items.map((u, i) => (
            <div key={u.id} className="card stack" style={{ gap: 8 }}>
              <div className="row-between">
                <strong>Unit {u.unit_number}</strong>
                <div className="row">
                  <span className="badge">{fromText(u.text).length} {t('vocab.words')}</span>
                  {u.is_default_open
                    ? <span className="badge badge-success">{t('book.autoOpen')}</span>
                    : <button className={`btn btn-sm ${u.open_for_students ? 'btn-ghost' : 'btn-primary'}`} onClick={() => setUnitAccess(u)}>
                      {u.open_for_students ? <><Lock size={14} /> {t('book.unitLockAction')}</> : <><Unlock size={14} /> {t('book.unitOpenAction')}</>}
                    </button>}
                </div>
              </div>
              <textarea className="textarea" style={{ minHeight: 130 }} value={u.text} onChange={e => setUnits({ ...units, items: units.items.map((x, k) => (k === i ? { ...x, text: e.target.value } : x)) })} />
              <button className="btn btn-primary btn-sm" style={{ alignSelf: 'flex-start' }} onClick={() => saveUnit(u)}>{t('common.save')}</button>
            </div>
          ))}
        </div>}
      </Modal>
    </div>
  );
}
