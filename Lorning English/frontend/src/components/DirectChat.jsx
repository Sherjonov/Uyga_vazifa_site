import { useCallback, useEffect, useRef, useState } from 'react';
import { ArrowLeft, Send, MessagesSquare } from 'lucide-react';
import { Empty, SkeletonList, Spinner } from './Loader';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';
import { fmtTime, initials } from '../utils/format';
import './DirectChat.css';

/** O'qituvchi <-> o'quvchi yozishmasi */
export default function DirectChat() {
  const { t, lang } = useLang();
  const toast = useToast();
  const [contacts, setContacts] = useState(null);
  const [active, setActive] = useState(null);
  const [thread, setThread] = useState([]);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [q, setQ] = useState('');
  const end = useRef(null);

  const loadContacts = useCallback(() => api.get('/messages/contacts').then(r => setContacts(r.data)).catch(() => setContacts([])), []);
  useEffect(() => { loadContacts(); }, [loadContacts]);

  const loadThread = useCallback(async id => {
    try { const { data } = await api.get(`/messages/thread/${id}`); setThread(data.messages); } catch (err) { toast.error(errMsg(err)); }
  }, [toast]);

  useEffect(() => {
    if (!active) return undefined;
    loadThread(active.id);
    const id = setInterval(() => loadThread(active.id), 8000); // yangi xabarlar uchun
    return () => clearInterval(id);
  }, [active, loadThread]);
  useEffect(() => { end.current?.scrollIntoView({ behavior: 'smooth' }); }, [thread]);

  const send = async e => {
    e.preventDefault();
    if (!text.trim() || !active) return;
    setSending(true);
    try {
      const { data } = await api.post('/messages', { recipient_id: active.id, body: text.trim() });
      setThread(list => [...list, data]);
      setText('');
    } catch (err) { toast.error(errMsg(err)); } finally { setSending(false); }
  };

  const filtered = (contacts || []).filter(c => c.name.toLowerCase().includes(q.toLowerCase()));

  return (
    <div className={`dchat card ${active ? 'has-active' : ''}`}>
      <aside className="dchat-list">
        <input className="input" placeholder={t('common.search')} value={q} onChange={e => setQ(e.target.value)} />
        <div className="dchat-contacts">
          {contacts === null ? <SkeletonList n={4} h={56} /> : filtered.length === 0 ? <Empty icon={MessagesSquare} title={t('chat.noContacts')} /> :
            filtered.map(c => (
              <button key={c.id} className={`dchat-contact ${active?.id === c.id ? 'active' : ''}`} onClick={() => { setActive(c); setContacts(list => list.map(x => (x.id === c.id ? { ...x, unread: 0 } : x))); }}>
                <span className="avatar">{initials(c.name)}</span>
                <span className="dchat-name"><strong>{c.name}</strong><small>{t(`role.${c.role}`)}</small></span>
                {c.unread > 0 && <span className="badge badge-primary">{c.unread}</span>}
              </button>
            ))}
        </div>
      </aside>
      <section className="dchat-thread">
        {!active ? <Empty icon={MessagesSquare} title={t('chat.pick')} /> : (
          <>
            <div className="dchat-head">
              <button className="btn btn-ghost btn-icon btn-sm dchat-back" onClick={() => setActive(null)}><ArrowLeft size={18} /></button>
              <span className="avatar">{initials(active.name)}</span><strong>{active.name}</strong>
            </div>
            <div className="dchat-msgs">
              {thread.length === 0 && <p className="muted center" style={{ margin: 'auto' }}>{t('chat.writeFirst')}</p>}
              {thread.map(m => (
                <div key={m.id} className={`bubble ${m.mine ? 'mine' : ''}`}><p>{m.body}</p><small>{fmtTime(m.created_at, lang)}</small></div>
              ))}
              <div ref={end} />
            </div>
            <form className="dchat-input" onSubmit={send}>
              <input className="input" value={text} onChange={e => setText(e.target.value)} placeholder={t('chat.placeholder')} maxLength={4000} />
              <button className="btn btn-primary btn-icon" disabled={sending || !text.trim()}>{sending ? <Spinner size={16} /> : <Send size={18} />}</button>
            </form>
          </>
        )}
      </section>
    </div>
  );
}
