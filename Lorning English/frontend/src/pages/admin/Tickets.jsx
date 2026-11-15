import { useCallback, useEffect, useState } from 'react';
import { Inbox, Save } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import { TICKET_BADGE } from '../../components/TicketBox';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDateTime } from '../../utils/format';
import './admin.css';

function Ticket({ tk, onSaved }) {
  const { t, lang } = useLang();
  const toast = useToast();
  const [status, setStatus] = useState(tk.status);
  const [reply, setReply] = useState(tk.admin_reply || '');
  const [busy, setBusy] = useState(false);
  const save = async () => {
    setBusy(true);
    try { await api.put(`/admin/tickets/${tk.id}`, { status, admin_reply: reply }); toast.success(t('common.saved')); onSaved(); } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  return (
    <div className={`card ticket ${tk.status === 'new' ? 'open-new' : ''}`}>
      <div className="row-between"><div><strong>{tk.subject}</strong><div className="hint">{tk.author_name} · {t(`role.${tk.author_role}`)} · {fmtDateTime(tk.created_at, lang)}</div></div><span className={`badge ${TICKET_BADGE[tk.status]}`}>{t(`ticket.status.${tk.status}`)}</span></div>
      <p className="text-2" style={{ whiteSpace: 'pre-wrap' }}>{tk.body}</p>
      <textarea className="textarea" style={{ minHeight: 80 }} value={reply} onChange={e => setReply(e.target.value)} placeholder={t('admin.replyPh')} />
      <div className="row"><select className="select" style={{ width: 'auto' }} value={status} onChange={e => setStatus(e.target.value)}>{['new', 'in_progress', 'resolved'].map(s => <option key={s} value={s}>{t(`ticket.status.${s}`)}</option>)}</select>
        <button className="btn btn-primary" onClick={save} disabled={busy}>{busy ? <Spinner size={16} /> : <Save size={16} />} {t('common.save')}</button></div>
    </div>
  );
}

export default function Tickets() {
  const { t } = useLang();
  const [status, setStatus] = useState('');
  const [items, setItems] = useState(null);
  const load = useCallback(() => api.get('/admin/tickets', { params: status ? { status } : {} }).then(r => setItems(r.data)).catch(() => setItems([])), [status]);
  useEffect(() => { setItems(null); load(); }, [load]);
  return (
    <div className="page">
      <PageHeader icon={Inbox} title={t('nav.tickets')} subtitle={t('admin.ticketsSub')}
        actions={<div className="tabs">{['', 'new', 'in_progress', 'resolved'].map(s => <button key={s} className={`tab ${status === s ? 'active' : ''}`} onClick={() => setStatus(s)}>{s ? t(`ticket.status.${s}`) : t('common.all')}</button>)}</div>} />
      {items === null ? <SkeletonList n={3} h={150} /> : items.length === 0 ? <div className="card"><Empty icon={Inbox} title={t('ticket.empty')} /></div> : <div className="stack stagger">{items.map(tk => <Ticket key={`${tk.id}-${tk.updated_at}`} tk={tk} onSaved={load} />)}</div>}
    </div>
  );
}
