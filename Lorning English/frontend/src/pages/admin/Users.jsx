import { useCallback, useEffect, useState } from 'react';
import { Ban, ChevronLeft, ChevronRight, CheckCircle2, Search, Users as UsersIcon } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { Empty } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDate, initials } from '../../utils/format';

export default function Users() {
  const { user: me } = useAuth();
  const { t, lang } = useLang();
  const toast = useToast();
  const [q, setQ] = useState('');
  const [role, setRole] = useState('');
  const [track, setTrack] = useState('');
  const [page, setPage] = useState(1);
  const [data, setData] = useState(null);

  const load = useCallback(() => {
    api.get('/admin/users', { params: { q: q || undefined, role: role || undefined, track: track || undefined, page, size: 20 } }).then(r => setData(r.data)).catch(() => setData({ items: [], total: 0 }));
  }, [q, role, track, page]);
  useEffect(() => { const id = setTimeout(load, 300); return () => clearTimeout(id); }, [load]);
  useEffect(() => { setPage(1); }, [q, role, track]);

  const block = async u => {
    try { await api.put(`/admin/users/${u.id}/block`, null, { params: { blocked: u.is_active } }); toast.success(t('common.saved')); load(); } catch (err) { toast.error(errMsg(err)); }
  };

  const cols = [
    { key: 'name', title: t('auth.fullName'), render: u => <div className="row" style={{ flexWrap: 'nowrap' }}><span className="avatar">{initials(u.name)}</span><div><strong>{u.name}</strong><div className="hint">{u.email || u.phone}</div></div></div> },
    { key: 'role', title: t('admin.role'), render: u => <span className="badge badge-primary">{t(`role.${u.role}`)}</span> },
    { key: 'score', title: t('students.score'), render: u => u.total_score },
    { key: 'created', title: t('admin.registered'), render: u => fmtDate(u.created_at, lang) },
    { key: 'st', title: t('parents.status'), render: u => <span className={`badge ${u.is_active ? 'badge-success' : 'badge-danger'}`}>{u.is_active ? t('admin.active') : t('admin.blocked')}</span> },
    { key: 'a', title: '', render: u => u.id !== me.id && <button className={`btn btn-sm ${u.is_active ? 'btn-danger' : 'btn-success'}`} onClick={() => block(u)}>{u.is_active ? <><Ban size={14} /> {t('admin.block')}</> : <><CheckCircle2 size={14} /> {t('admin.unblock')}</>}</button> }
  ];
  const pages = data ? Math.max(1, Math.ceil(data.total / 20)) : 1;

  return (
    <div className="page page-wide">
      <PageHeader icon={UsersIcon} title={t('nav.users')} subtitle={t('admin.usersSub')} />
      <div className="row" style={{ marginBottom: 16 }}>
        <div style={{ position: 'relative', flex: 1, minWidth: 220 }}><Search size={18} style={{ position: 'absolute', left: 14, top: 13, color: 'var(--text-3)' }} /><input className="input" style={{ paddingLeft: 44 }} placeholder={t('common.search')} value={q} onChange={e => setQ(e.target.value)} /></div>
        <select className="select" style={{ width: 'auto' }} value={role} onChange={e => setRole(e.target.value)}><option value="">{t('admin.allRoles')}</option>{['student', 'teacher', 'admin'].map(r => <option key={r} value={r}>{t(`role.${r}`)}</option>)}</select>
      </div>
      <DataTable columns={cols} rows={data?.items || []} loading={!data} empty={<Empty icon={UsersIcon} title={t('admin.noUsers')} />} />
      <div className="row-between" style={{ marginTop: 16 }}><span className="muted">{data?.total ?? 0} {t('admin.users').toLowerCase()}</span>
        <div className="row"><button className="btn btn-ghost btn-icon btn-sm" disabled={page <= 1} onClick={() => setPage(p => p - 1)}><ChevronLeft size={16} /></button><span className="mono">{page} / {pages}</span><button className="btn btn-ghost btn-icon btn-sm" disabled={page >= pages} onClick={() => setPage(p => p + 1)}><ChevronRight size={16} /></button></div></div>
    </div>
  );
}
