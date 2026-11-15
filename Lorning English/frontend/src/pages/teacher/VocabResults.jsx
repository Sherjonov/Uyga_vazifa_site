import { useEffect, useState } from 'react';
import { ListChecks } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import Modal from '../../components/Modal';
import DataTable from '../../components/DataTable';
import { Empty } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDateTime } from '../../utils/format';
import '../../styles/extra.css';

const badge = a => (a.kicked_out ? <span className="badge badge-danger">{'⛔'} Chiqarildi</span> : a.passed ? <span className="badge badge-success">O'tdi</span> : <span className="badge badge-danger">O'tmadi</span>);

/** Topshirilgan lug'atlar: natija, topilgan/topilmagan so'zlar, ogohlantirishlar va kamera rasmi */
export default function VocabResults() {
  const { t, lang } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [rows, setRows] = useState(null);
  const [detail, setDetail] = useState(null);

  useEffect(() => {
    if (gl) return;
    setRows(null);
    api.get('/vocab/attempts', { params: groupId ? { group_id: groupId } : {} }).then(r => setRows(r.data)).catch(() => setRows([]));
  }, [gl, groupId]);

  const open = async a => {
    try {
      const { data } = await api.get(`/vocab/attempts/${a.id}`); setDetail(data);
    } catch (err) { toast.error(errMsg(err)); }
  };

  const cols = [
    { key: 's', title: t('students.student'), render: a => <strong>{a.student_name}</strong> },
    { key: 'g', title: t('groups.group'), render: a => a.group_name },
    { key: 'u', title: 'Unit', render: a => `${a.book_title} · Unit ${a.unit_number}` },
    { key: 'r', title: t('vocab.result'), render: badge },
    { key: 'sc', title: t('students.score'), render: a => <span className="score-pill">{a.score}</span> },
    { key: 'w', title: t('vocab.warns'), render: a => <span className={`badge ${a.warnings_count ? 'badge-warning' : ''}`}>{a.warnings_count}</span> },
    { key: 'd', title: t('vocab.date'), render: a => fmtDateTime(a.finished_at || a.created_at, lang) },
  ];

  return (
    <div className="page page-wide">
      <PageHeader icon={ListChecks} title={t('nav.vocabResults')} subtitle={t('vocab.resultsSub')} />
      <div style={{ marginBottom: 16 }}><GroupSelect groups={groups} value={groupId} onChange={setGroupId} /></div>
      <DataTable columns={cols} rows={rows || []} loading={rows === null} onRowClick={open} empty={<Empty icon={ListChecks} title={t('vocab.noResults')} />} />
      <Modal open={!!detail} onClose={() => setDetail(null)} size="lg" title={detail ? `${detail.student_name} — Unit ${detail.unit_number}` : ''}>
        {detail && <div className="stack">
          <div className="row">{badge(detail)}<span className="badge">{detail.percent}%</span><span className="badge badge-warning">{t('vocab.warns')}: {detail.warnings_count}</span></div>
          <div className="grid grid-2" style={{ alignItems: 'start' }}>
            <div><h4 style={{ color: 'var(--success)' }}>✅ {t('vocab.found')} ({detail.found.length})</h4>
              <table className="vx-words"><tbody>{detail.found.map((w, i) => <tr key={i}><td>{w.en} {w.practice && <span className="badge">{t('vx.practice')}</span>}</td><td>{w.uz}</td></tr>)}</tbody></table></div>
            <div><h4 style={{ color: 'var(--danger)' }}>❌ {t('vocab.missedList')} ({detail.missed.length})</h4>
              <table className="vx-words"><tbody>{detail.missed.map((w, i) => <tr key={i}><td>{w.en} {w.practice && <span className="badge">{t('vx.practice')}</span>}</td><td>{w.uz}</td><td className="hint">{w.answer != null && w.answer !== '' ? String(w.answer) : '—'}</td></tr>)}</tbody></table></div>
          </div>
          {detail.violations.length > 0 && <div><h4>⚠️ {t('vocab.violations')}</h4><ul style={{ paddingLeft: 18 }}>{detail.violations.map((v, i) => <li key={i}>{t(`vx.kind.${v.kind}`) !== `vx.kind.${v.kind}` ? t(`vx.kind.${v.kind}`) : v.kind} · {fmtDateTime(v.at, lang)}</li>)}</ul></div>}
        </div>}
      </Modal>
    </div>
  );
}
