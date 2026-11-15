import { useEffect, useMemo, useState } from 'react';
import { Send } from 'lucide-react';
import Modal from './Modal';
import { Spinner } from './Loader';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';

/** O'quvchining ota-onasiga xabar. Botga ulangan ota-onalardan bittasini tanlab, to'g'ridan-to'g'ri
 *  uning Telegram profiliga yuborish mumkin; SMS/email ham saqlangan. */
export default function ParentMessageModal({ student, parentLinkId, onClose, onSent }) {
  const { t } = useLang();
  const toast = useToast();
  const [body, setBody] = useState('');
  const [contact, setContact] = useState(null);
  const [target, setTarget] = useState('');
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  const tgParents = student?.telegram_parents || [];

  useEffect(() => {
    if (!student) return;
    setLoading(true);
    Promise.all([api.get(`/parents/${student.id}/template`), api.get(`/parents/${student.id}/contact`)])
      .then(([tpl, c]) => { setBody(tpl.data.body); setContact(c.data); })
      .catch(err => toast.error(errMsg(err)))
      .finally(() => setLoading(false));
    setTarget(parentLinkId ? `tg:${parentLinkId}` : tgParents[0] ? `tg:${tgParents[0].link_id}` : '');
  }, [student, parentLinkId]); // eslint-disable-line react-hooks/exhaustive-deps

  const options = useMemo(() => {
    const o = tgParents.map(p => ({ key: `tg:${p.link_id}`, icon: '✈️', title: p.name || (p.username ? `@${p.username}` : 'Telegram'),
      sub: [p.phone, p.username && `@${p.username}`].filter(Boolean).join(' · '), tag: t('parents.viaTelegram'), warn: p.blocked }));
    if (contact?.phone) o.push({ key: 'sms', icon: '📱', title: 'SMS', sub: contact.phone, tag: contact.parent_name || '' });
    if (contact?.email) o.push({ key: 'email', icon: '✉️', title: 'Email', sub: contact.email, tag: contact.parent_name || '' });
    if (o.length > 1) o.push({ key: 'all', icon: '👨‍👩‍👧', title: t('parents.toAll'), sub: t('parents.toAllHint'), tag: '' });
    return o;
  }, [tgParents, contact, t]);

  // tanlangan variant yo'qolib qolsa, birinchisiga o'tamiz
  useEffect(() => { if (!loading && options.length && !options.some(o => o.key === target)) setTarget(options[0].key); }, [options, loading]); // eslint-disable-line react-hooks/exhaustive-deps

  const saveContact = async () => {
    try { const { data } = await api.put(`/parents/${student.id}/contact`, contact); setContact(data); toast.success(t('common.saved')); } catch (err) { toast.error(errMsg(err)); }
  };

  const send = async () => {
    const payload = { student_id: student.id, body };
    if (target.startsWith('tg:')) Object.assign(payload, { channel: 'telegram', parent_link_id: Number(target.slice(3)) });
    else Object.assign(payload, { channel: target === 'all' ? 'auto' : target });
    setBusy(true);
    try {
      const { data } = await api.post('/parents/send', payload);
      toast.success(t('parents.sentTo', { n: data.results.length }));
      onSent?.();
      onClose();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <Modal open={!!student} onClose={onClose} title={`${t('parents.messageTo')}: ${student?.name || ''}`} size="lg"
      footer={<><button className="btn btn-ghost" onClick={onClose}>{t('common.cancel')}</button>
        <button className="btn btn-primary" disabled={busy || loading || !options.length || !target || !body.trim()} onClick={send}>
          {busy ? <Spinner size={16} /> : <Send size={16} />} {t('common.send')}</button></>}>
      {loading ? <div className="center" style={{ padding: 30 }}><Spinner size={30} /></div> : (
        <div className="stack">
          <div className="field" style={{ marginBottom: 0 }}>
            <label>{t('parents.pickParent')}</label>
            {options.length === 0 ? <div className="alert alert-warning">{t('parents.noRecipients')}</div> : (
              <div className="stack" style={{ gap: 8 }}>
                {options.map(o => (
                  <label key={o.key} className="parent-opt" data-on={target === o.key}>
                    <input type="radio" name="parent-target" checked={target === o.key} onChange={() => setTarget(o.key)} />
                    <span className="parent-opt-icon">{o.icon}</span>
                    <span className="parent-opt-main"><strong>{o.title}</strong><small>{o.sub}</small></span>
                    {o.warn ? <span className="badge badge-warning">{t('parents.tgBlocked')}</span> : o.tag ? <span className="badge badge-info">{o.tag}</span> : null}
                  </label>
                ))}
              </div>
            )}
          </div>

          <div className="field" style={{ marginBottom: 0 }}><label>{t('parents.text')}</label>
            <textarea className="textarea" style={{ minHeight: 190 }} value={body} onChange={e => setBody(e.target.value)} maxLength={1500} /></div>

          <details className="parent-contact-edit">
            <summary>{t('parents.contact')} (SMS / Email)</summary>
            <div className="grid grid-3" style={{ gap: 10, width: '100%', marginTop: 10 }}>
              <input className="input input-sm" placeholder={t('profile.parentName')} value={contact?.parent_name || ''} onChange={e => setContact({ ...contact, parent_name: e.target.value })} />
              <input className="input input-sm" placeholder="+998901234567" value={contact?.phone || ''} onChange={e => setContact({ ...contact, phone: e.target.value })} />
              <input className="input input-sm" placeholder="Email" value={contact?.email || ''} onChange={e => setContact({ ...contact, email: e.target.value })} />
            </div>
            <button className="btn btn-sm btn-ghost" style={{ marginTop: 10 }} onClick={saveContact}>{t('common.save')}</button>
          </details>
        </div>
      )}
    </Modal>
  );
}
