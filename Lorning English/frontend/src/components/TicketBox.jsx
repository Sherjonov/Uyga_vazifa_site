import { useCallback, useEffect, useState } from 'react';
import { Send, LifeBuoy } from 'lucide-react';
import { Empty, SkeletonList, Spinner } from './Loader';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';
import { fmtDateTime } from '../utils/format';

export const TICKET_BADGE = { new: 'badge-info', in_progress: 'badge-warning', resolved: 'badge-success' };

/** Adminga murojaat (taklif/kamchilik) formasi va yuborilgan murojaatlar */
export default function TicketBox() {
  const { t, lang } = useLang();
  const toast = useToast();
  const [items, setItems] = useState(null);
  const [subject, setSubject] = useState('');
  const [body, setBody] = useState('');
  const [busy, setBusy] = useState(false);

  const load = useCallback(() => api.get('/tickets/mine').then(r => setItems(r.data)).catch(() => setItems([])), []);
  useEffect(() => { load(); }, [load]);

  const send = async e => {
    e.preventDefault();
    if (subject.trim().length < 3 || body.trim().length < 5) return toast.error(t('err.fillAll'));
    setBusy(true);
    try {
      await api.post('/tickets', { subject, body });
      toast.success(t('ticket.sent'));
      setSubject(''); setBody('');
      load();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <div className="grid grid-2" style={{ alignItems: 'start' }}>
      <form className="card" onSubmit={send}>
        <div className="card-title"><h3>{t('ticket.new')}</h3></div>
        <div className="field"><label>{t('ticket.subject')}</label><input className="input" value={subject} onChange={e => setSubject(e.target.value)} maxLength={200} /></div>
        <div className="field"><label>{t('ticket.body')}</label><textarea className="textarea" value={body} onChange={e => setBody(e.target.value)} placeholder={t('ticket.bodyPh')} /></div>
        <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner size={16} /> : <Send size={16} />} {t('common.send')}</button>
      </form>
      <div className="stack">
        <h3>{t('ticket.mine')}</h3>
        {items === null ? <SkeletonList n={2} /> : items.length === 0 ? <div className="card"><Empty icon={LifeBuoy} title={t('ticket.empty')} /></div> :
          items.map(tk => (
            <div key={tk.id} className="card">
              <div className="row-between"><strong>{tk.subject}</strong><span className={`badge ${TICKET_BADGE[tk.status]}`}>{t(`ticket.status.${tk.status}`)}</span></div>
              <p className="text-2" style={{ marginTop: 8, whiteSpace: 'pre-wrap' }}>{tk.body}</p>
              <span className="hint">{fmtDateTime(tk.created_at, lang)}</span>
              {tk.admin_reply && <div className="alert alert-success" style={{ marginTop: 12, flexDirection: 'column', gap: 4 }}><strong>{t('ticket.adminReply')}</strong><span style={{ whiteSpace: 'pre-wrap' }}>{tk.admin_reply}</span></div>}
            </div>
          ))}
      </div>
    </div>
  );
}
