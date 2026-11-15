import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { ListPlus, Pencil, Plus, Search, Trash2, UserPlus, Users, UsersRound } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import Modal from '../../components/Modal';
import DataTable from '../../components/DataTable';
import { Empty, Spinner } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { initials, num, todayStr } from '../../utils/format';
import './teacher.css';

const STATUSES = ['present', 'late', 'absent', 'excused'];

export default function Students() {
  const { user } = useAuth();
  const { t } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, group, loading: gl, reload } = useGroups();
  const [date, setDate] = useState(todayStr());
  const [rows, setRows] = useState(null);
  const [penalty, setPenalty] = useState(20);
  const [newGroup, setNewGroup] = useState(null);
  const [addOpen, setAddOpen] = useState(false);
  const [q, setQ] = useState('');
  const [found, setFound] = useState([]);
  const [searching, setSearching] = useState(false);
  const [namesOpen, setNamesOpen] = useState(false);
  const [namesText, setNamesText] = useState('');
  const [namesBusy, setNamesBusy] = useState(false);

  useEffect(() => { api.get('/settings/teacher').then(r => setPenalty(r.data.absence_penalty)).catch(() => {}); }, []);

  const load = useCallback(async () => {
    if (!groupId) return setRows([]);
    try {
      const [att, mem] = await Promise.all([api.get(`/attendance/${groupId}`, { params: { date } }), api.get(`/groups/${groupId}/members`)]);
      const phones = Object.fromEntries(mem.data.map(m => [m.id, m]));
      setRows(att.data.students.map(s => ({ ...s, phone: phones[s.id]?.phone, email: phones[s.id]?.email, claimed: phones[s.id]?.claimed !== false })));
    } catch (err) { toast.error(errMsg(err)); setRows([]); }
  }, [groupId, date, toast]);
  useEffect(() => { if (!gl) { setRows(null); load(); } }, [gl, load]);

  const mark = async (s, status) => {
    const next = s.status === status ? null : status; // qayta bosilsa belgi olib tashlanadi
    setRows(list => list.map(r => (r.id === s.id ? { ...r, status: next } : r)));
    try {
      await api.put('/attendance', { group_id: groupId, student_id: s.id, date, status: next });
      load();
    } catch (err) { toast.error(errMsg(err)); load(); }
  };
  const markAll = async () => {
    if (!window.confirm(t('students.allPresentConfirm'))) return;
    try { await api.put('/attendance/bulk', { group_id: groupId, date, status: 'present' }); load(); } catch (err) { toast.error(errMsg(err)); }
  };

  const createGroup = async () => {
    if (!newGroup.name.trim()) return toast.error(t('err.fillAll'));
    try {
      const { data } = await api.post('/groups', newGroup);
      await reload(); setGroupId(data.id); setNewGroup(null); toast.success(t('groups.created'));
    } catch (err) { toast.error(errMsg(err)); }
  };
  const renameGroup = async () => {
    const name = window.prompt(t('groups.rename'), group.name);
    if (!name?.trim()) return;
    try { await api.put(`/groups/${groupId}`, { name }); reload(); } catch (err) { toast.error(errMsg(err)); }
  };
  const deleteGroup = async () => {
    if (!window.confirm(t('groups.deleteConfirm'))) return;
    try { await api.delete(`/groups/${groupId}`); localStorage.removeItem('aedu_group'); await reload(); } catch (err) { toast.error(errMsg(err)); }
  };

  // O'quvchini ism yoki telefon bo'yicha qidirish (kechiktirib)
  useEffect(() => {
    if (!addOpen || q.trim().length < 2) { setFound([]); return undefined; }
    setSearching(true);
    const id = setTimeout(() => {
      api.get('/groups/search-students', { params: { q: q.trim(), group_id: groupId } }).then(r => setFound(r.data)).catch(() => setFound([])).finally(() => setSearching(false));
    }, 350);
    return () => clearTimeout(id);
  }, [q, addOpen, groupId]);

  const addStudent = async s => {
    try { await api.post(`/groups/${groupId}/members`, { student_id: s.id }); setFound(f => f.map(x => (x.id === s.id ? { ...x, is_member: true } : x))); load(); reload(); toast.success(t('students.added', { name: s.name })); } catch (err) { toast.error(errMsg(err)); }
  };
  // O'qituvchi faqat ismlarni kiritadi: o'quvchi ro'yxatdan o'tayotganda guruhini tanlab, ismini topadi
  const addNames = async () => {
    const names = namesText.split('\n').map(x => x.trim()).filter(Boolean);
    if (!names.length) return toast.error(t('err.fillAll'));
    setNamesBusy(true);
    try {
      const { data } = await api.post('/roster', { group_id: groupId, names });
      toast.success(t('students.namesCreated', { n: data.created.length }) + (data.skipped.length ? ` · ${t('students.namesSkipped', { n: data.skipped.length })}` : ''));
      setNamesText(''); setNamesOpen(false); load(); reload();
    } catch (err) { toast.error(errMsg(err)); } finally { setNamesBusy(false); }
  };
  const renameName = async s => {
    const name = window.prompt(t('students.renamePrompt'), s.name);
    if (!name?.trim() || name.trim() === s.name) return;
    try { await api.put(`/roster/${s.id}`, { name }); load(); } catch (err) { toast.error(errMsg(err)); }
  };
  const removeStudent = async s => {
    if (!window.confirm(t('students.removeConfirm', { name: s.name }))) return;
    try { await api.delete(`/groups/${groupId}/members/${s.id}`); load(); reload(); } catch (err) { toast.error(errMsg(err)); }
  };
  const columns = [
    { key: 'n', title: '#', width: 50, render: (_, i) => <span className="muted">{i + 1}</span> },
    { key: 'name', title: t('students.student'), render: s => <div className="person"><span className="avatar">{initials(s.name)}</span><div><strong>{s.name}</strong><small>{s.claimed ? (s.phone || s.email) : t('students.notRegistered')}</small></div></div> },
    { key: 'score', title: t('students.score'), render: s => <strong className="mono">{num(s.total_score, 1)}</strong> },
    { key: 'abs', title: t('students.absences'), render: s => <span className={`badge ${s.absent_total >= 3 ? 'badge-danger' : ''}`}>{s.absent_total} / {s.late_total || 0} / {s.excused_total}</span> },
    { key: 'status', title: t('students.today'), render: s => (
      <div className="att-seg">{STATUSES.map(st => <button key={st} className={s.status === st ? `on-${st}` : ''} onClick={() => mark(s, st)}>{t(`att.${st}`)}</button>)}</div>
    ) },
    { key: 'x', title: '', width: 210, render: s => <div className="row" style={{ gap: 6, flexWrap: 'nowrap' }}>
      <Link className="btn btn-ghost btn-sm student-knowledge-link" to={`/teacher/students/${s.id}?group_id=${groupId}`}>{t('students.knowledge')}</Link>
      {!s.claimed && <button className="btn btn-ghost btn-icon btn-sm" onClick={() => renameName(s)} title={t('students.rename')}><Pencil size={15} /></button>}
      <button className="btn btn-danger btn-icon btn-sm" onClick={() => removeStudent(s)} aria-label="remove"><Trash2 size={15} /></button>
    </div> }
  ];

  return (
    <div className="page page-wide">
      <PageHeader icon={Users} title={t('nav.students')} subtitle={t('students.subtitle')}
        actions={<button className="btn btn-primary" onClick={() => setNewGroup({ name: '', kind: 'english' })}><Plus size={17} /> {t('groups.create')}</button>} />

      {!gl && groups.length === 0 ? (
        <div className="card"><Empty icon={UsersRound} title={t('groups.none')} text={t('groups.noneText')} action={<button className="btn btn-primary" onClick={() => setNewGroup({ name: '', kind: 'english' })}><Plus size={16} /> {t('groups.create')}</button>} /></div>
      ) : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="row-between">
            <GroupSelect groups={groups} value={groupId} onChange={setGroupId} />
            <div className="row">
              {group && <span className="badge badge-primary">{group.members_count}</span>}
              <button className="btn btn-ghost btn-icon btn-sm" onClick={renameGroup} title={t('groups.rename')}><Pencil size={15} /></button>
              <button className="btn btn-danger btn-icon btn-sm" onClick={deleteGroup}><Trash2 size={15} /></button>
            </div>
          </div>
          <div className="row-between">
            <div className="row"><input className="input" style={{ width: 'auto' }} type="date" value={date} onChange={e => setDate(e.target.value)} />
              <button className="btn btn-ghost" onClick={markAll} disabled={!rows?.length}>{t('students.allPresent')}</button></div>
            <div className="row"><button className="btn btn-primary" onClick={() => setNamesOpen(true)}><ListPlus size={17} /> {t('students.addNames')}</button>
              <button className="btn btn-ghost" onClick={() => { setQ(''); setFound([]); setAddOpen(true); }}><UserPlus size={17} /> {t('students.add')}</button></div>
          </div>
          <div className="alert alert-info">{t('students.penaltyNote', { n: penalty })}</div>
          <DataTable columns={columns} rows={rows || []} loading={rows === null} empty={<Empty icon={Users} title={t('students.empty')} text={t('students.emptyText')} />} />
        </div>
      )}

      <Modal open={!!newGroup} onClose={() => setNewGroup(null)} title={t('groups.create')} size="sm"
        footer={<><button className="btn btn-ghost" onClick={() => setNewGroup(null)}>{t('common.cancel')}</button><button className="btn btn-primary" onClick={createGroup}>{t('common.create')}</button></>}>
        {newGroup && <>
          <div className="field" style={{ marginBottom: 0 }}><label>{t('groups.name')}</label><input className="input" autoFocus value={newGroup.name} onChange={e => setNewGroup({ ...newGroup, name: e.target.value })} placeholder="Beginner 1" maxLength={120} /></div>
        </>}
      </Modal>

      <Modal open={namesOpen} onClose={() => setNamesOpen(false)} title={t('students.addNames')} size="md"
        footer={<><button className="btn btn-ghost" onClick={() => setNamesOpen(false)}>{t('common.cancel')}</button><button className="btn btn-primary" disabled={namesBusy} onClick={addNames}>{namesBusy ? <Spinner size={16} /> : <Plus size={16} />} {t('common.add')}</button></>}>
        <div className="alert alert-info" style={{ marginBottom: 14 }}>{t('students.namesHint')}</div>
        <textarea className="textarea" style={{ minHeight: 220 }} autoFocus value={namesText} onChange={e => setNamesText(e.target.value)} placeholder={t('students.namesPh')} />
      </Modal>

      <Modal open={addOpen} onClose={() => setAddOpen(false)} title={t('students.add')} size="md">
        <div className="input-icon" style={{ position: 'relative', marginBottom: 14 }}>
          <Search size={18} style={{ position: 'absolute', left: 14, top: 13, color: 'var(--text-3)' }} />
          <input className="input" style={{ paddingLeft: 44 }} autoFocus value={q} onChange={e => setQ(e.target.value)} placeholder={t('students.searchPh')} />
        </div>
        <div className="stack" style={{ gap: 8, minHeight: 120 }}>
          {searching && <div className="center"><Spinner /></div>}
          {!searching && q.trim().length >= 2 && found.length === 0 && <p className="muted center">{t('students.notFound')}</p>}
          {found.map(s => (
            <div key={s.id} className="list-item"><span className="avatar">{initials(s.name)}</span>
              <div className="spacer"><strong>{s.name}</strong><div className="hint">{s.phone || s.email}</div></div>
              {s.is_member ? <span className="badge badge-success">{t('students.inGroup')}</span> : <button className="btn btn-primary btn-sm" onClick={() => addStudent(s)}><Plus size={15} /> {t('common.add')}</button>}
            </div>
          ))}
        </div>
      </Modal>

    </div>
  );
}
