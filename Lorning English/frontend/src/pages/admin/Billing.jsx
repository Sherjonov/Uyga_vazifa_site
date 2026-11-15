import { useCallback, useEffect, useState } from 'react';
import { AlertTriangle, Check, Wallet, X } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DataTable from '../../components/DataTable';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtCountdown, fmtDateTime, fmtFull, fmtMoney } from '../../utils/format';
import useNow from '../../utils/useNow';
import { isImage } from '../../utils/files';
import './admin.css';

const PAY_BADGE = { pending: 'badge-warning', approved: 'badge-success', rejected: 'badge-danger' };

function PaymentCard({ p, onDone }) {
  const { t, lang } = useLang();
  const toast = useToast();
  const [note, setNote] = useState('');
  const [busy, setBusy] = useState('');
  const act = async action => {
    if (action === 'fraud' && !window.confirm(t('billing.fakeConfirm'))) return;
    setBusy(action);
    try {
      const { data } = await api.put(`/admin/payments/${p.id}`, { action, note });
      toast.success(action === 'approve'
        ? t('billing.approvedMsg', { d: fmtFull(data.subscription_until, lang) })
        : action === 'fraud' ? t('billing.fraudMsg') : t('billing.rejectedMsg'));
      onDone();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(''); }
  };
  return (
    <div className="card pay-review">
      <div className="pay-receipt">
        {isImage(p.receipt_url) ? <a href={p.receipt_url} target="_blank" rel="noreferrer"><img src={p.receipt_url} alt="receipt" /></a> : <a className="btn btn-ghost" href={p.receipt_url} target="_blank" rel="noreferrer">PDF</a>}
      </div>
      <div className="stack" style={{ gap: 10, flex: 1, minWidth: 220 }}>
        <div className="row-between">
          <div>
            <strong>{p.teacher.name}</strong>
            <div className="hint">{p.teacher.email || p.teacher.phone}</div>
            {p.fake_receipt_warning && <span className="badge badge-warning" style={{ marginTop: 6 }}><AlertTriangle size={13} /> {t('billing.fakeWarning')}</span>}
          </div>
          <span className={`badge ${PAY_BADGE[p.status]}`}>{t(`sub.st.${p.status}`)}</span>
        </div>
        <div className="row"><span className="badge badge-primary">{t('sub.months', { n: p.months })}</span><strong className="mono">{fmtMoney(p.amount)} {t('sub.som')}</strong><span className="hint">{fmtDateTime(p.created_at, lang)}</span></div>
        <div className="hint">{t('billing.currentUntil')}: <strong className="mono">{fmtFull(p.subscription_until, lang)}</strong></div>
        {p.period_end && <div className="hint">{t('billing.reviewPeriod')}: <strong className="mono">{fmtFull(p.period_end, lang)}</strong></div>}
        {p.status === 'pending' ? (
          <>
            <input className="input input-sm" value={note} onChange={e => setNote(e.target.value)} placeholder={t('billing.notePh')} maxLength={500} />
            <div className="row">
              <button className="btn btn-success" disabled={!!busy} onClick={() => act('approve')}>{busy === 'approve' ? <Spinner size={16} /> : <Check size={16} />} {t('billing.approve', { n: p.months })}</button>
              <button className="btn btn-danger" disabled={!!busy} onClick={() => act('reject')}>{busy === 'reject' ? <Spinner size={16} /> : <X size={16} />} {t('retake.reject')}</button>
              <button className="btn btn-danger" disabled={!!busy} onClick={() => act('fraud')}>{busy === 'fraud' ? <Spinner size={16} /> : <AlertTriangle size={16} />} {t('billing.fakeReceipt')}</button>
            </div>
          </>
        ) : <div className="hint">
          {p.status === 'approved' ? `${t('sub.validUntil')}: ${fmtFull(p.period_end, lang)}` : ''}
          {p.is_fraudulent && <span className="badge badge-warning" style={{ marginLeft: 8 }}><AlertTriangle size={13} /> {t('billing.fakeWarning')}</span>}
          {p.admin_note}
        </div>}
      </div>
    </div>
  );
}

function Payments() {
  const { t } = useLang();
  const [status, setStatus] = useState('pending');
  const [items, setItems] = useState(null);
  const load = useCallback(() => api.get('/admin/payments', { params: status ? { status } : {} }).then(r => setItems(r.data)).catch(() => setItems([])), [status]);
  useEffect(() => { setItems(null); load(); }, [load]);
  return (
    <div className="stack">
      <div className="tabs" style={{ alignSelf: 'flex-start' }}>{['pending', 'approved', 'rejected', ''].map(s => <button key={s} className={`tab ${status === s ? 'active' : ''}`} onClick={() => setStatus(s)}>{s ? t(`sub.st.${s}`) : t('common.all')}</button>)}</div>
      {items === null ? <SkeletonList n={2} h={150} /> : items.length === 0 ? <div className="card"><Empty icon={Wallet} title={t('billing.noPayments')} /></div> : items.map(p => <PaymentCard key={`${p.id}-${p.status}`} p={p} onDone={load} />)}
    </div>
  );
}

function Subscriptions() {
  const { t, lang } = useLang();
  const now = useNow(1000);
  const [rows, setRows] = useState(null);
  useEffect(() => { const load = () => api.get('/admin/subscriptions').then(r => setRows(r.data)).catch(() => setRows([])); load(); const id = setInterval(load, 30000); return () => clearInterval(id); }, []);
  const cols = [
    { key: 'name', title: t('role.teacher'), render: u => <div><strong>{u.name}</strong><div className="hint">{u.email || u.phone}</div></div> },
    { key: 'st', title: t('parents.status'), render: u => { const left = u.until ? (new Date(u.until) - now) / 1000 : null; const act = left == null || left > 0; return <span className={`badge ${act ? (u.trial ? 'badge-info' : 'badge-success') : 'badge-danger'}`}>{!act ? t('sub.expiredShort') : u.trial ? t('sub.trialShort') : t('sub.activeShort')}</span>; } },
    { key: 'until', title: t('billing.endsAt'), render: u => <span className="mono">{fmtFull(u.until, lang)}</span> },
    { key: 'left', title: t('billing.remaining'), render: u => { const left = u.until ? (new Date(u.until) - now) / 1000 : 0; return <strong className="mono" style={{ color: left > 0 ? 'var(--text)' : 'var(--danger)' }}>{left > 0 ? fmtCountdown(left, t) : '00:00:00'}</strong>; } },
    { key: 'paid', title: t('billing.paidTotal'), render: u => `${fmtMoney(u.paid_total)} ${t('sub.som')}` },
    { key: 'pending', title: t('sub.st.pending'), render: u => (u.pending ? <span className="badge badge-warning">{u.pending}</span> : '–') },
    { key: 'warning', title: t('billing.warning'), render: u => u.fake_receipt_warning ? <span className="badge badge-warning"><AlertTriangle size={13} /> {t('billing.fakeWarning')}</span> : '–' },
  ];
  return <DataTable columns={cols} rows={rows || []} loading={rows === null} empty={<Empty title={t('billing.noTeachers')} />} />;
}

export default function Billing() {
  const { t } = useLang();
  const [tab, setTab] = useState('payments');
  return (
    <div className="page page-wide">
      <PageHeader icon={Wallet} title={t('nav.billing')} subtitle={t('billing.subtitle')}
        actions={<div className="tabs"><button className={`tab ${tab === 'payments' ? 'active' : ''}`} onClick={() => setTab('payments')}>{t('billing.payments')}</button><button className={`tab ${tab === 'subs' ? 'active' : ''}`} onClick={() => setTab('subs')}>{t('billing.subscriptions')}</button></div>} />
      {tab === 'payments' ? <Payments /> : <Subscriptions />}
    </div>
  );
}
