import { useEffect, useState } from 'react';
import { Layers, Search } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { Empty } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import api from '../../api/axios';
import { fmtDate } from '../../utils/format';

export default function Groups() {
  const { t, lang } = useLang();
  const [q, setQ] = useState('');
  const [rows, setRows] = useState(null);
  useEffect(() => { const id = setTimeout(() => api.get('/admin/groups', { params: q ? { q } : {} }).then(r => setRows(r.data)).catch(() => setRows([])), 300); return () => clearTimeout(id); }, [q]);
  const cols = [
    { key: 'name', title: t('groups.name'), render: g => <strong>{g.name}</strong> },
    { key: 'teacher_name', title: t('role.teacher') },
    { key: 'members_count', title: t('admin.members') },
    { key: 'created_at', title: t('admin.registered'), render: g => fmtDate(g.created_at, lang) }
  ];
  return (
    <div className="page page-wide">
      <PageHeader icon={Layers} title={t('nav.groups')} subtitle={t('admin.groupsSub')} />
      <div style={{ position: 'relative', maxWidth: 420, marginBottom: 16 }}><Search size={18} style={{ position: 'absolute', left: 14, top: 13, color: 'var(--text-3)' }} /><input className="input" style={{ paddingLeft: 44 }} placeholder={t('common.search')} value={q} onChange={e => setQ(e.target.value)} /></div>
      <DataTable columns={cols} rows={rows || []} loading={rows === null} empty={<Empty icon={Layers} title={t('admin.noGroups')} />} />
    </div>
  );
}
