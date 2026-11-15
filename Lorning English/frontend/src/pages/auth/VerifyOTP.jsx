import { useCallback, useEffect, useRef, useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { ArrowLeft, Check, Eye, EyeOff, Lock, ShieldCheck, User } from 'lucide-react';
import AuthShell from '../../components/AuthShell';
import OtpInput from '../../components/OtpInput';
import { Spinner } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { homeFor } from '../../utils/format';
import '../../components/AuthForm.css';

const strength = p => (p.length >= 10 && /[A-Za-z]/.test(p) && /\d/.test(p) ? 3 : p.length >= 8 ? 2 : p.length >= 6 ? 1 : 0);

export default function VerifyOTP() {
  const { state } = useLocation();
  const nav = useNavigate();
  const { t } = useLang();
  const { startSession } = useAuth();
  const toast = useToast();

  const [step, setStep] = useState('otp'); // otp | password
  const [code, setCode] = useState('');
  const [busy, setBusy] = useState(false);
  const [bad, setBad] = useState(false);
  const [left, setLeft] = useState(state?.resendIn ?? 60);
  const [regToken, setRegToken] = useState('');
  const [name, setName] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [devCode, setDevCode] = useState(state?.devCode || null);
  const [bot, setBot] = useState({ via: state?.via, url: state?.botUrl, linked: state?.tgLinked });
  const typing = useRef(null);
  const submitted = useRef('');

  const identifier = state?.identifier;
  const channel = state?.channel;

  // 60 soniyalik "qayta yuborish" taymeri
  useEffect(() => {
    if (left <= 0) return undefined;
    const id = setTimeout(() => setLeft(l => l - 1), 1000);
    return () => clearTimeout(id);
  }, [left]);

  // Kodni avtomatik terib berish (DEV rejimida server kodni qaytaradi): raqamlar birma-bir yoziladi
  const autoType = useCallback(full => {
    clearInterval(typing.current);
    let i = 0;
    setCode('');
    typing.current = setInterval(() => {
      i += 1;
      setCode(full.slice(0, i));
      if (i >= full.length) clearInterval(typing.current);
    }, 170);
  }, []);

  useEffect(() => {
    if (devCode && step === 'otp') { const id = setTimeout(() => autoType(devCode), 500); return () => clearTimeout(id); }
    return undefined;
  }, [devCode, step, autoType]);
  useEffect(() => () => clearInterval(typing.current), []);

  // Android Chrome: SMS dan kodni avtomatik o'qish (WebOTP API)
  useEffect(() => {
    if (channel !== 'phone' || !('OTPCredential' in window) || step !== 'otp') return undefined;
    const ac = new AbortController();
    navigator.credentials
      .get({ otp: { transport: ['sms'] }, signal: ac.signal })
      .then(cred => cred?.code && setCode(cred.code))
      .catch(() => {});
    return () => ac.abort();
  }, [channel, step]);

  const verify = useCallback(
    async value => {
      if (busy || submitted.current === value) return;
      submitted.current = value;
      setBusy(true);
      setBad(false);
      try {
        const { data } = await api.post('/auth/register/verify', { identifier, code: value });
        if (state.student) {  // o'quvchi: guruh -> ism tanlangan, parol kiritilgan. Kod tasdiqlangach hisob tayyor.
          const r = await api.post('/auth/register/student', { group_id: state.student.group_id, name: state.student.name, password: state.password, registration_token: data.registration_token });
          startSession(r.data.access_token, r.data.user);
          nav('/student/home', { replace: true });
          return;
        }
        setRegToken(data.registration_token);
        setStep('password');
      } catch (err) {
        setBad(true);
        toast.error(errMsg(err));
        setCode('');
        submitted.current = '';
        if (err?.response?.data?.code === 'roster_not_found') nav('/register');
      } finally {
        setBusy(false);
      }
    },
    [busy, identifier, toast]
  );

  // 6 ta raqam to'lishi bilan avtomatik tekshiriladi
  useEffect(() => { if (code.length === 6 && step === 'otp') verify(code); }, [code, step, verify]);

  const resend = async () => {
    try {
      const { data } = await api.post('/auth/register/request', { identifier });
      setLeft(data.resend_in);
      setCode('');
      submitted.current = '';
      setDevCode(data.dev_code || null);
      setBot({ via: data.via, url: data.bot_url, linked: data.telegram_linked });
      toast.success(t('auth.codeSent'));
    } catch (err) {
      toast.error(errMsg(err));
    }
  };

  const complete = async e => {
    e.preventDefault();
    if (name.trim().length < 2 || password.length < 6) return toast.error(t('err.passwordShort'));
    setBusy(true);
    try {
      const { data } = await api.post('/auth/register/complete', { registration_token: regToken, name: name.trim(), password });
      startSession(data.access_token, data.user, false);
      nav(homeFor(data.user), { replace: true });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  if (!identifier) return <Navigate to="/register" replace />;

  return (
    <AuthShell>
      {step === 'otp' ? (
        <div className="step-anim" key="otp">
          <button className="link-btn row" onClick={() => nav('/register')} style={{ marginBottom: 14 }}><ArrowLeft size={16} /> {t('common.back')}</button>
          <div className="stat-icon" style={{ marginBottom: 14 }}><ShieldCheck size={24} /></div>
          <h1>{t('auth.verifyTitle')}</h1>
          <p className="auth-sub">{t('auth.verifySub', { to: identifier })}</p>
          <OtpInput value={code} onChange={setCode} disabled={busy} error={bad} />
          {devCode && <p className="hint center" style={{ marginTop: 14 }}>{t('auth.devHint')}</p>}
          {channel === 'phone' && !devCode && bot.via !== 'telegram' && <p className="hint center" style={{ marginTop: 14 }}>{t('auth.smsAuto')}</p>}
          {bot.via === 'telegram' && (
            <div className="card stack" style={{ marginTop: 16, gap: 8, textAlign: 'center' }}>
              <p>{bot.linked ? `✈️ ${t('auth.tgSent')}` : `✈️ ${t('auth.tgNeed')}`}</p>
              {bot.url && <a className={`btn ${bot.linked ? 'btn-ghost' : 'btn-primary'}`} href={bot.url} target="_blank" rel="noreferrer">{t('auth.tgOpen')}</a>}
            </div>
          )}
          <div className="center" style={{ marginTop: 22 }}>
            {busy ? <Spinner /> : left > 0 ? (
              <span className="muted">{t('auth.resendIn', { s: left })}</span>
            ) : (
              <button className="btn btn-ghost" onClick={resend}>{t('auth.resend')}</button>
            )}
          </div>
        </div>
      ) : (
        <form className="step-anim" key="pw" onSubmit={complete} noValidate>
          <div className="stat-icon success" style={{ marginBottom: 14 }}><Check size={24} /></div>
          <h1>{t('auth.setPasswordTitle')}</h1>
          <p className="auth-sub">{t('auth.setPasswordSub')}</p>
          <div className="field">
            <label>{t('auth.fullName')}</label>
            <div className="input-icon"><User size={18} /><input className="input" value={name} onChange={e => setName(e.target.value)} placeholder={t('auth.fullNamePh')} autoComplete="name" autoFocus /></div>
          </div>
          <div className="field has-eye">
            <label>{t('auth.password')}</label>
            <div className="input-icon">
              <Lock size={18} />
              <input className="input" type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" autoComplete="new-password" />
              <button type="button" className="eye" onClick={() => setShow(s => !s)}>{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
            </div>
            <div className="pw-meter">{[1, 2, 3].map(i => <span key={i} className={strength(password) >= i ? `on-${strength(password)}` : ''} />)}</div>
            <span className="hint">{t('auth.passwordHint')}</span>
          </div>
          <button className="btn btn-primary btn-block" disabled={busy} style={{ minHeight: 48 }}>{busy && <Spinner size={18} />} {t('auth.finish')}</button>
        </form>
      )}
    </AuthShell>
  );
}
