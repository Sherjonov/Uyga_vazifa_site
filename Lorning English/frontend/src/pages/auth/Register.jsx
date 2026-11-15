import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { ArrowLeft, ArrowRight, Eye, EyeOff, GraduationCap, Lock, Mail, Phone, Presentation, UserRound } from 'lucide-react';
import AuthShell from '../../components/AuthShell';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import '../../components/AuthForm.css';
import './JoinGroup.css';
import './Register.css';

const formatPhone = v => {
  const d = v.replace(/\D/g, '').replace(/^998/, '').slice(0, 9);
  const p = [d.slice(0, 2), d.slice(2, 5), d.slice(5, 7), d.slice(7, 9)].filter(Boolean).join(' ');
  return `+998 ${p}`;
};
const strength = p => (p.length >= 10 && /[A-Za-z]/.test(p) && /\d/.test(p) ? 3 : p.length >= 8 ? 2 : p.length >= 6 ? 1 : 0);

/** O'quvchi: 1) guruhni tanlaydi 2) ismini topadi 3) telefon/email va parol -> ro'yxatdan o'tadi */
function StudentRegister() {
  const { t } = useLang();
  const { startSession } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [step, setStep] = useState(1);
  const [groups, setGroups] = useState(null);
  const [group, setGroup] = useState(null);
  const [fullName, setFullName] = useState('');
  const [method, setMethod] = useState('phone');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('+998 ');
  const [password, setPassword] = useState('');
  const [password2, setPassword2] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);
  const [requireOtp, setRequireOtp] = useState(true);

  useEffect(() => {
    api.get('/roster/public/groups').then(r => setGroups(r.data)).catch(() => setGroups([]));
    api.get('/auth/config').then(r => setRequireOtp(r.data.require_otp)).catch(() => {});
  }, []);

  const pick = { group_id: group?.id, name: fullName.trim().replace(/\s+/g, ' ') };

  const submit = async e => {
    e.preventDefault();
    const identifier = method === 'email' ? email.trim() : phone.replace(/\s/g, '');
    if (method === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(identifier)) return toast.error(t('err.email'));
    if (method === 'phone' && !/^\+998\d{9}$/.test(identifier)) return toast.error(t('err.phone'));
    if (password.length < 6) return toast.error(t('err.passwordShort'));
    if (password !== password2) return toast.error(t('err.passwordMismatch'));
    setBusy(true);
    try {
      if (requireOtp && method === 'phone') {
        // Telefon: tasdiqlash kodi Telegram botga yuboriladi
        const { data } = await api.post('/auth/register/request', { identifier });
        nav('/verify', { state: { identifier: data.identifier, channel: data.channel, resendIn: data.resend_in, devCode: data.dev_code, via: data.via, botUrl: data.bot_url, tgLinked: data.telegram_linked, student: pick, password } });
      } else {
        // Email: kod kerak emas, faqat parol bilan ro'yxatdan o'tiladi
        const { data } = await api.post('/auth/register/student', { group_id: pick.group_id, name: pick.name, password, identifier });
        startSession(data.access_token, data.user);
        nav('/student/home', { replace: true });
      }
    } catch (err) {
      toast.error(errMsg(err));
      if (err?.response?.data?.code === 'group_not_found') { setStep(1); setGroup(null); }
    } finally { setBusy(false); }
  };

  return (
    <div>
      <div className="reg-steps">{[1, 2, 3].map(i => <span key={i} className={step >= i ? 'on' : ''} />)}</div>

      {step === 1 && (
        <div className="step-anim" key="s1">
          <h1>{t('join.title')}</h1>
          <p className="auth-sub">{t('reg.pickGroupSub')}</p>
          {groups === null ? <SkeletonList n={2} h={76} /> : groups.length === 0 ? (
            <Empty icon={GraduationCap} title={t('reg.noGroupsYet')} text={t('reg.noGroupsYetText')} />
          ) : (
            <div className="join-groups">
              {groups.map(g => (
                <button key={g.id} type="button" className={`join-group ${group?.id === g.id ? 'selected' : ''}`} onClick={() => { setGroup(g); setStep(2); }}>
                  <strong>{g.name}</strong><span>{g.teacher_name}</span>
                </button>
              ))}
            </div>
          )}
        </div>
      )}

      {step === 2 && group && (
        <form className="step-anim" key="s2" noValidate onSubmit={e => { e.preventDefault(); if (pick.name.length < 2) return toast.error(t('err.nameShort')); setStep(3); }}>
          <button type="button" className="link-btn row" onClick={() => setStep(1)} style={{ marginBottom: 10 }}><ArrowLeft size={16} /> {t('common.back')}</button>
          <h1>{group.name}</h1>
          <p className="auth-sub">{t('reg.enterName')}</p>
          <div className="field">
            <label>{t('reg.fullName')}</label>
            <div className="input-icon">
              <UserRound size={18} />
              <input className="input" value={fullName} maxLength={120} onChange={e => setFullName(e.target.value)} placeholder={t('reg.fullNamePh')} autoComplete="name" autoFocus />
            </div>
          </div>
          <button className="btn btn-primary btn-block" style={{ minHeight: 48, marginTop: 14 }} disabled={pick.name.length < 2}>{t('common.next')} <ArrowRight size={18} /></button>
        </form>
      )}

      {step === 3 && group && (
        <form className="step-anim" key="s3" onSubmit={submit} noValidate>
          <button type="button" className="link-btn row" onClick={() => setStep(2)} style={{ marginBottom: 10 }}><ArrowLeft size={16} /> {t('common.back')}</button>
          <div className="reg-picked"><span className="avatar">{pick.name.slice(0, 1).toUpperCase()}</span><div><strong>{pick.name}</strong><div className="hint">{group.name}</div></div></div>
          <div className="seg">
            <button type="button" className={method === 'phone' ? 'active' : ''} onClick={() => setMethod('phone')}><Phone size={17} /> {t('auth.phone')}</button>
            <button type="button" className={method === 'email' ? 'active' : ''} onClick={() => setMethod('email')}><Mail size={17} /> Email</button>
          </div>
          <div className="field step-anim" key={method}>
            <label>{method === 'email' ? 'Email' : t('auth.phone')}</label>
            <div className="input-icon">
              {method === 'email' ? <Mail size={18} /> : <Phone size={18} />}
              {method === 'email'
                ? <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com" autoComplete="email" autoFocus />
                : <input className="input" type="tel" value={phone} onChange={e => setPhone(formatPhone(e.target.value))} placeholder="+998 90 123 45 67" autoComplete="tel" autoFocus />}
            </div>
            {method === 'phone' && requireOtp && <span className="hint">✈️ {t('otp.tgPhoneHint')}</span>}
          </div>
          <div className="field has-eye">
            <label>{t('auth.password')}</label>
            <div className="input-icon">
              <Lock size={18} />
              <input className="input" type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" autoComplete="new-password" />
              <button type="button" className="eye" onClick={() => setShow(s => !s)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </div>
            <div className="pw-meter">{[1, 2, 3].map(i => <span key={i} className={strength(password) >= i ? `on-${strength(password)}` : ''} />)}</div>
          </div>
          <div className="field">
            <label>{t('reg.passwordRepeat')}</label>
            <div className="input-icon">
              <Lock size={18} />
              <input className="input" type={show ? 'text' : 'password'} value={password2} onChange={e => setPassword2(e.target.value)} placeholder="••••••••" autoComplete="new-password" />
            </div>
            {password2 && password !== password2 && <span className="hint" style={{ color: 'var(--danger)' }}>{t('err.passwordMismatch')}</span>}
          </div>
          <button className="btn btn-primary btn-block" disabled={busy} style={{ minHeight: 50 }}>{busy ? <Spinner size={18} /> : <UserRound size={18} />} {t('auth.register')}</button>
        </form>
      )}
    </div>
  );
}

/** O'qituvchi: email/telefon -> kod -> parol -> yo'nalish */
function TeacherRegister() {
  const { t } = useLang();
  const toast = useToast();
  const nav = useNavigate();
  const [method, setMethod] = useState('email');
  const [email, setEmail] = useState('');
  const [phone, setPhone] = useState('+998 ');
  const [busy, setBusy] = useState(false);

  const submit = async e => {
    e.preventDefault();
    const identifier = method === 'email' ? email.trim() : phone.replace(/\s/g, '');
    if (method === 'email' && !/^[^@\s]+@[^@\s]+\.[^@\s]{2,}$/.test(identifier)) return toast.error(t('err.email'));
    if (method === 'phone' && !/^\+998\d{9}$/.test(identifier)) return toast.error(t('err.phone'));
    setBusy(true);
    try {
      const { data } = await api.post('/auth/register/request', { identifier });
      nav('/verify', { state: { identifier: data.identifier, channel: data.channel, resendIn: data.resend_in, devCode: data.dev_code, via: data.via } });
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <div className="step-anim">
      <h1>{t('auth.createAccount')}</h1>
      <p className="auth-sub">{t('reg.teacherSub')}</p>
      <div className="seg">
        <button type="button" className={method === 'email' ? 'active' : ''} onClick={() => setMethod('email')}><Mail size={17} /> Email</button>
        <button type="button" className={method === 'phone' ? 'active' : ''} onClick={() => setMethod('phone')}><Phone size={17} /> {t('auth.phone')}</button>
      </div>
      <form onSubmit={submit} noValidate>
        <div className="field step-anim" key={method}>
          <label>{method === 'email' ? 'Email' : t('auth.phone')}</label>
          <div className="input-icon">
            {method === 'email' ? <Mail size={18} /> : <Phone size={18} />}
            {method === 'email'
              ? <input className="input" type="email" value={email} onChange={e => setEmail(e.target.value)} placeholder="name@example.com" autoComplete="email" autoFocus />
              : <input className="input" type="tel" value={phone} onChange={e => setPhone(formatPhone(e.target.value))} placeholder="+998 90 123 45 67" autoComplete="tel" autoFocus />}
          </div>
          <span className="hint">{method === 'email' ? t('auth.emailHint') : t('auth.phoneHint')}</span>
          {method === 'phone' && <span className="hint">✈️ {t('otp.tgPhoneHint')}</span>}
        </div>
        <button className="btn btn-primary btn-block" disabled={busy} style={{ minHeight: 48 }}>{busy && <Spinner size={18} />} {t('auth.sendCode')} <ArrowRight size={18} /></button>
      </form>
      <p className="join-hint">{t('reg.trialNote')}</p>
    </div>
  );
}

export default function Register() {
  const { t } = useLang();
  const [mode, setMode] = useState('student');
  return (
    <AuthShell>
      <div className="seg" style={{ marginBottom: 20 }}>
        <button type="button" className={mode === 'student' ? 'active' : ''} onClick={() => setMode('student')}><GraduationCap size={17} /> {t('reg.iAmStudent')}</button>
        <button type="button" className={mode === 'teacher' ? 'active' : ''} onClick={() => setMode('teacher')}><Presentation size={17} /> {t('reg.iAmTeacher')}</button>
      </div>
      {mode === 'student' ? <StudentRegister /> : <TeacherRegister />}
      <p className="auth-foot">{t('auth.haveAccount')} <Link to="/login"><strong>{t('reg.alreadyLogin')}</strong></Link></p>
    </AuthShell>
  );
}
