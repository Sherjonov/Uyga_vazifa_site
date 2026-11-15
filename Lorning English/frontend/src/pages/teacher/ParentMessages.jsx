import { useCallback, useEffect, useState } from 'react';
import { Copy, ExternalLink, PhoneCall, Send, X } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import ParentMessageModal from '../../components/ParentMessageModal';
import { Empty } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDateTime, initials } from '../../utils/format';
import './teacher.css';

export default function ParentMessages() {
  const { t, lang } = useLang();
  const toast = useToast();
  const [students, setStudents] = useState(null);
  const [history, setHistory] = useState(null);
  const [bot, setBot] = useState(null);
  const [sel, setSel] = useState(null);       // { student, linkId }

  const load = useCallback(() => {
    api.get('/parents/students').then(r => setStudents(r.data)).catch(() => setStudents([]));
    api.get('/parents/history').then(r => setHistory(r.data)).catch(() => setHistory([]));
  }, []);
  useEffect(() => { load(); api.get('/telegram/info').then(r => setBot(r.data)).catch(() => setBot({ enabled: false })); }, [load]);

  const copy = async () => { try { await navigator.clipboard.writeText(bot.url); toast.success(t('common.copied')); } catch { toast.error(bot.url); } };
  const unlink = async (s, p) => {
    if (!window.confirm(t('parents.unlinkConfirm', { name: p.name || '', student: s.name }))) return;
    try { await api.delete(`/parents/links/${p.link_id}`); toast.success(t('parents.unlinked')); load(); } catch (err) { toast.error(errMsg(err)); }
  };

  const cols = [
    { key: 'name', title: t('students.student'), render: s => <div className="person"><span className="avatar">{initials(s.name)}</span><strong>{s.name}</strong></div> },
    { key: 'c', title: t('parents.contact'), render: s => (
      <div className="stack" style={{ gap: 6 }}>
        {s.telegram_parents.map(p => (
          <div key={p.link_id} className="parent-chip">
            <span className="parent-chip-main">✈️ <strong>{p.name || (p.username ? `@${p.username}` : 'Telegram')}</strong>{p.phone && <span className="muted"> {p.phone}</span>}{p.blocked && <span className="badge badge-warning" style={{ marginLeft: 6 }}>{t('parents.tgBlocked')}</span>}</span>
            <button className="btn btn-ghost btn-sm" onClick={() => setSel({ student: s, linkId: p.link_id })} title={t('parents.write')}><Send size={13} /></button>
            <button className="btn btn-ghost btn-sm" onClick={() => unlink(s, p)} title={t('parents.unlink')}><X size={13} /></button>
          </div>
        ))}
        {(s.contact.phone || s.contact.email) && <span className="muted" style={{ fontSize: '0.85rem' }}>{s.contact.parent_name || ''} {[s.contact.phone, s.contact.email].filter(Boolean).join(' · ')}</span>}
        {!s.has_contact && <span className="badge badge-warning">{t('parents.noContact')}</span>}
        {s.has_contact && s.telegram_parents.length === 0 && <span className="badge">{t('parents.noLinked')}</span>}
      </div>) },
    { key: 'a', title: '', width: 160, render: s => <button className="btn btn-primary btn-sm" disabled={!s.has_contact} onClick={() => setSel({ student: s, linkId: null })}><Send size={14} /> {t('parents.write')}</button> }
  ];
  const hcols = [
    { key: 'created_at', title: t('parents.when'), render: m => fmtDateTime(m.created_at, lang) },
    { key: 'student_name', title: t('students.student') },
    { key: 'channel', title: t('parents.channel'), render: m => <span className="badge">{m.channel.toUpperCase()}</span> },
    { key: 'recipient', title: t('parents.to') },
    { key: 'body', title: t('parents.text'), render: m => <span className="text-2" title={m.body}>{m.body.slice(0, 70)}{m.body.length > 70 ? '…' : ''}</span> },
    { key: 'status', title: t('parents.status'), render: m => <span className={`badge ${m.status === 'failed' ? 'badge-danger' : m.status === 'dev' ? 'badge-info' : 'badge-success'}`}>{t(`parents.st.${m.status}`)}</span> }
  ];

  return (
    <div className="page page-wide">
      <PageHeader icon={PhoneCall} title={t('nav.parents')} subtitle={t('parents.subtitle')} />
      <div className="stack" style={{ gap: 26 }}>
        <div className="card parent-bot">
          <div className="parent-bot-icon">✈️</div>
          <div className="parent-bot-text">
            <strong>{t('parents.botTitle')}</strong>
            {bot?.enabled
              ? <p>{t('parents.botText', { bot: bot.username ? `@${bot.username}` : 'bot' })}</p>
              : <p>{t('parents.botOff')}</p>}
          </div>
          {bot?.enabled && bot.url && <div className="row" style={{ flexWrap: 'nowrap' }}>
            <button className="btn btn-ghost btn-sm" onClick={copy}><Copy size={14} /> {t('parents.botCopy')}</button>
            <a className="btn btn-primary btn-sm" href={bot.url} target="_blank" rel="noreferrer"><ExternalLink size={14} /> {t('parents.botOpen')}</a>
          </div>}
        </div>
        <DataTable columns={cols} rows={students || []} loading={students === null} empty={<Empty icon={PhoneCall} title={t('students.empty')} />} />
        <div><h3 style={{ marginBottom: 12 }}>{t('parents.history')}</h3>
          <DataTable columns={hcols} rows={history || []} loading={history === null} empty={<Empty title={t('parents.noHistory')} />} /></div>
      </div>
      <ParentMessageModal student={sel?.student} parentLinkId={sel?.linkId} onClose={() => setSel(null)} onSent={load} />
    </div>
  );
}
