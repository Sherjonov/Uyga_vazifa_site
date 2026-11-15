import { useCallback, useEffect, useRef, useState } from 'react';
import { Pencil, Plus, Table2, Trash2 } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import Modal from '../../components/Modal';
import { Empty, SkeletonList } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import './teacher.css';

export default function Grid() {
  const { t } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [data, setData] = useState(null);
  const [cells, setCells] = useState({});
  const [flash, setFlash] = useState({});
  const [colModal, setColModal] = useState(null);
  const saved = useRef({});

  const load = useCallback(async () => {
    if (!groupId) return setData({ columns: [], students: [], cells: {} });
    try { const { data: d } = await api.get(`/grid/${groupId}`); setData(d); setCells(d.cells); saved.current = { ...d.cells }; } catch (err) { toast.error(errMsg(err)); setData({ columns: [], students: [], cells: {} }); }
  }, [groupId, toast]);
  useEffect(() => { if (!gl) { setData(null); load(); } }, [gl, load]);

  const max = data?.max_score ?? 50;
  const saveCell = async (col, stu) => {
    const key = `${col}_${stu}`;
    const value = (cells[key] || '').trim();
    if (value === (saved.current[key] || '')) return;
    const num = Number(value.replace(',', '.'));
    if (value && !Number.isNaN(num) && (num < 0 || num > max)) {  // o'qituvchi sozlamasidagi chegaradan yuqori baho qo'yib bo'lmaydi
      toast.error(t('grid.tooHigh', { max }));
      setCells(c => ({ ...c, [key]: saved.current[key] || '' }));
      return;
    }
    setFlash(f => ({ ...f, [key]: 'saving' }));
    try {
      await api.put('/grid/cells', { column_id: col, student_id: stu, value });
      saved.current[key] = value;
      setFlash(f => ({ ...f, [key]: 'saved' }));
      setTimeout(() => setFlash(f => ({ ...f, [key]: '' })), 900);
    } catch (err) { toast.error(errMsg(err)); setFlash(f => ({ ...f, [key]: '' })); }
  };

  const submitColumn = async () => {
    const title = colModal.title.trim();
    if (!title) return;
    try {
      if (colModal.id) await api.put(`/grid/columns/${colModal.id}`, { title }); else await api.post(`/grid/${groupId}/columns`, { title });
      setColModal(null); load();
    } catch (err) { toast.error(errMsg(err)); }
  };
  const deleteColumn = async c => {
    if (!window.confirm(t('grid.deleteColumnConfirm', { name: c.title }))) return;
    try { await api.delete(`/grid/columns/${c.id}`); load(); } catch (err) { toast.error(errMsg(err)); }
  };

  return (
    <div className="page page-wide">
      <PageHeader icon={Table2} title={t('nav.grid')} subtitle={`${t('grid.subtitle')} ${t('grid.maxHint', { max })}`}
        actions={groupId && <button className="btn btn-primary" onClick={() => setColModal({ title: '' })}><Plus size={17} /> {t('grid.addColumn')}</button>} />
      {!gl && groups.length === 0 ? <div className="card"><Empty icon={Table2} title={t('groups.none')} text={t('groups.noneText')} /></div> : (
        <div className="stack" style={{ gap: 18 }}>
          <GroupSelect groups={groups} value={groupId} onChange={setGroupId} />
          {data === null ? <SkeletonList n={4} h={52} /> : data.students.length === 0 ? <div className="card"><Empty icon={Table2} title={t('students.empty')} text={t('students.emptyText')} /></div> : (
            <div className="table-wrap">
              <table className="grid-table">
                <thead><tr>
                  <th>{t('students.student')}</th>
                  {data.columns.map(c => (
                    <th key={c.id} className="col-head">{c.title}
                      <div className="col-acts"><button onClick={() => setColModal({ id: c.id, title: c.title })} aria-label="rename"><Pencil size={13} /></button><button onClick={() => deleteColumn(c)} aria-label="delete"><Trash2 size={13} /></button></div>
                    </th>
                  ))}
                </tr></thead>
                <tbody>
                  {data.students.map(s => (
                    <tr key={s.id}>
                      <td><strong>{s.name}</strong></td>
                      {data.columns.map(c => {
                        const key = `${c.id}_${s.id}`;
                        return (
                          <td key={c.id}>
                            <input className={`cell-in ${flash[key] || ''}`} value={cells[key] || ''} maxLength={40} placeholder={`0–${max}`}
                              onChange={e => setCells({ ...cells, [key]: e.target.value })} onBlur={() => saveCell(c.id, s.id)}
                              onKeyDown={e => e.key === 'Enter' && e.target.blur()} />
                          </td>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
              {data.columns.length === 0 && <p className="muted center" style={{ padding: 22 }}>{t('grid.noColumns')}</p>}
            </div>
          )}
        </div>
      )}
      <Modal open={!!colModal} onClose={() => setColModal(null)} title={colModal?.id ? t('grid.renameColumn') : t('grid.addColumn')} size="sm"
        footer={<><button className="btn btn-ghost" onClick={() => setColModal(null)}>{t('common.cancel')}</button><button className="btn btn-primary" onClick={submitColumn}>{t('common.save')}</button></>}>
        {colModal && <div className="field" style={{ marginBottom: 0 }}><label>{t('grid.columnName')}</label><input className="input" autoFocus value={colModal.title} onChange={e => setColModal({ ...colModal, title: e.target.value })} onKeyDown={e => e.key === 'Enter' && submitColumn()} placeholder={t('grid.columnPh')} maxLength={80} /></div>}
      </Modal>
    </div>
  );
}
