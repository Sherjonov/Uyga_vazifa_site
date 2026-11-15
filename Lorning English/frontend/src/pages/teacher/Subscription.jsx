import { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { AlertTriangle, BadgeCheck, Clock, Copy, CreditCard, Crown, Gift, LifeBuoy, Lock, Send, Sparkles, UploadCloud } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import Modal from '../../components/Modal';
import FileChips from '../../components/FileChips';
import { Skeleton, Spinner } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtCountdown, fmtDateTime, fmtFull, fmtMoney } from '../../utils/format';
import useNow from '../../utils/useNow';
import './teacher.css';

const PAY_BADGE = { pending: 'badge-warning', approved: 'badge-success', rejected: 'badge-danger' };

function PayModal({ plan, card, onClose, onDone }) {
  const { t } = useLang();
  const toast = useToast();
  const [file, setFile] = useState(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  const preview = useMemo(() => (file && file.type.startsWith('image/') ? URL.createObjectURL(file) : null), [file]);
  useEffect(() => () => preview && URL.revokeObjectURL(preview), [preview]);

  const copy = () => { navigator.clipboard?.writeText(card.number.replace(/\s/g, '')); toast.success(t('sub.copied')); };
  const pick = list => { const f = list?.[0]; if (f) setFile(f); };
  const send = async () => {
    if (!file) return toast.error(t('sub.receiptRequired'));
    const fd = new FormData();
    fd.append('months', plan.months); fd.append('receipt', file);
    setBusy(true);
    try { await api.post('/subscription/pay', fd); toast.success(t('sub.sent')); onDone(); } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <Modal open={!!plan} onClose={onClose} title={t('sub.payTitle')} size="md"
      footer={<><button className="btn btn-ghost" onClick={onClose}>{t('common.cancel')}</button><button className="btn btn-primary" disabled={busy || !file} onClick={send}>{busy ? <Spinner size={16} /> : <Send size={16} />} {t('sub.activate')}</button></>}
      >
      {plan && (
        <div className="stack" onPaste={e => { const f = [...(e.clipboardData?.files || [])].find(x => x.type.startsWith('image/')); if (f) { e.preventDefault(); setFile(f); } }}>
          <div className="pay-amount"><span>{t('sub.months', { n: plan.months })}</span><strong>{fmtMoney(plan.price)} {t('sub.som')}</strong></div>
          <div className="pay-card">
            <CreditCard size={22} />
            <div className="spacer"><div className="hint">{t('sub.cardNumber')}</div><div className="pay-num mono">{card.number}</div>{card.owner && <div className="hint">{card.owner}</div>}</div>
            <button className="btn btn-ghost btn-sm" onClick={copy}><Copy size={14} /> {t('sub.copy')}</button>
          </div>
          <ol className="pay-steps"><li>{t('sub.step1', { sum: fmtMoney(plan.price) })}</li><li>{t('sub.step2')}</li><li>{t('sub.step3')}</li></ol>
          <div className={`drop ${over ? 'over' : ''}`} onClick={() => input.current?.click()} onDragOver={e => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)} onDrop={e => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files); }}>
            {preview ? <img src={preview} alt="" style={{ maxHeight: 220, maxWidth: '100%', borderRadius: 12 }} /> : <UploadCloud size={32} />}
            <strong>{file ? file.name : t('sub.dropReceipt')}</strong><span className="hint">{t('sub.receiptHint')}</span>
            <input ref={input} type="file" accept=".png,.jpg,.jpeg,.webp,.pdf" hidden onChange={e => pick(e.target.files)} />
          </div>
        </div>
      )}
    </Modal>
  );
}

export default function Subscription() {
  const { t, lang } = useLang();
  const { refresh } = useAuth();
  const now = useNow(1000);
  const [data, setData] = useState(null);
  const [payments, setPayments] = useState(null);
  const [plan, setPlan] = useState(null);

  const load = useCallback(() => {
    api.get('/subscription').then(r => setData(r.data)).catch(() => {});
    api.get('/subscription/payments').then(r => setPayments(r.data)).catch(() => setPayments([]));
  }, []);
  useEffect(() => { load(); const id = setInterval(() => { load(); refresh().catch(() => {}); }, 15000); return () => clearInterval(id); }, [load, refresh]);

  const sub = data?.subscription;
  const left = sub?.until ? (new Date(sub.until) - now) / 1000 : null;
  const active = left == null || left > 0;
  const hasPending = payments?.some(p => p.status === 'pending');
  const best = !data?.fake_receipt_warning && data?.plans?.length ? data.plans[data.plans.length - 1].months : null;

  return (
    <div className="page">
      <PageHeader icon={Crown} title={t('nav.subscription')} subtitle={t('sub.subtitle')} />
      {!data ? <Skeleton h={150} r={24} /> : (
        <div className={`card sub-status ${active ? '' : 'expired'}`}>
          <div className="stat-icon" style={active ? undefined : { background: 'var(--danger-soft)', color: 'var(--danger)' }}>{active ? (sub.trial ? <Gift size={26} /> : <BadgeCheck size={26} />) : <Lock size={26} />}</div>
          <div className="spacer">
            <h2>{!active ? t('sub.expired') : sub.trial ? t('sub.trialTitle') : t('sub.activeTitle')}</h2>
            <p className="text-2">{t('sub.until')}: <strong className="mono">{fmtFull(sub.until, lang)}</strong></p>
            {active && left != null && <p className="sub-count mono"><Clock size={16} /> {fmtCountdown(left, t)}</p>}
          </div>
        </div>
      )}
      {data && !active && <div className="alert alert-danger" style={{ margin: '16px 0' }}><Lock size={18} /> <span>{t('sub.lockedText')}</span></div>}
      {data && sub.trial && active && <div className="alert alert-info" style={{ margin: '16px 0' }}><Sparkles size={18} /> <span>{t('sub.trialNote', { n: data.trial_days })}</span></div>}
      {hasPending && <div className="alert alert-warning" style={{ margin: '16px 0' }}><Clock size={18} /> <span>{t('sub.pendingNote')}</span></div>}
      {data?.fake_receipt_warning && <div className="alert alert-warning" style={{ margin: '16px 0' }}><AlertTriangle size={18} /> <span>{t('sub.fakeWarning')}</span></div>}

      <h3 style={{ margin: '24px 0 12px' }}>{t('sub.plans')}</h3>
      <div className="grid grid-4 stagger">
        {(data?.plans || []).map(p => (
          <div key={p.months} className={`card card-hover plan ${p.months === best ? 'best' : ''}`}>
            {p.months === best && <span className="plan-tag">{t('sub.bestValue')}</span>}
            <div className="plan-m">{t('sub.months', { n: p.months })}</div>
            <div className="plan-price">{fmtMoney(p.price)}<small> {t('sub.som')}</small></div>
            <div className="hint">{fmtMoney(p.per_month)} {t('sub.som')} / {t('sub.perMonth')}</div>
            {p.save > 0 ? <span className="badge badge-success">{t('sub.save', { n: fmtMoney(p.save) })}</span> : <span className="badge">&nbsp;</span>}
            <button className="btn btn-primary btn-block" disabled={hasPending} onClick={() => setPlan(p)}><CreditCard size={16} /> {t('sub.buy')}</button>
          </div>
        ))}
      </div>

      <div className="row-between" style={{ margin: '28px 0 12px' }}><h3>{t('sub.history')}</h3><Link to="/teacher/contact-admin" className="btn btn-ghost btn-sm"><LifeBuoy size={15} /> {t('sub.writeAdmin')}</Link></div>
      <div className="stack">
        {payments === null ? <Skeleton h={70} r={16} /> : payments.length === 0 ? <p className="muted">{t('sub.noPayments')}</p> : payments.map(p => (
          <div key={p.id} className="list-item" style={{ flexWrap: 'wrap' }}>
            <div className="spacer"><strong>{t('sub.months', { n: p.months })} · {fmtMoney(p.amount)} {t('sub.som')}</strong>
              <div className="hint">{fmtDateTime(p.created_at, lang)}{p.status === 'approved' ? ` · ${t('sub.validUntil')}: ${fmtFull(p.period_end, lang)}` : ''}{p.admin_note ? ` · ${p.admin_note}` : ''}</div></div>
            <FileChips urls={[p.receipt_url]} />
            {p.is_fraudulent && <span className="badge badge-warning"><AlertTriangle size={13} /> {t('billing.fakeWarning')}</span>}
            <span className={`badge ${PAY_BADGE[p.status]}`}>{t(`sub.st.${p.status}`)}</span>
          </div>
        ))}
      </div>
      {plan && <PayModal plan={plan} card={data.card} onClose={() => setPlan(null)} onDone={() => { setPlan(null); load(); }} />}
    </div>
  );
}
