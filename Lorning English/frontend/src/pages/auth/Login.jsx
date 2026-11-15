import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { Eye, EyeOff, Lock, LogIn, Mail } from 'lucide-react';
import AuthShell from '../../components/AuthShell';
import { Spinner } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import { errMsg } from '../../api/axios';
import { homeFor } from '../../utils/format';
import '../../components/AuthForm.css';

export default function Login() {
  const { t } = useLang();
  const { login } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [identifier, setIdentifier] = useState('');
  const [password, setPassword] = useState('');
  const [show, setShow] = useState(false);
  const [busy, setBusy] = useState(false);

  const submit = async e => {
    e.preventDefault();
    if (!identifier.trim() || !password) return toast.error(t('err.fillAll'));
    setBusy(true);
    try {
      const u = await login(identifier.trim(), password);
      nav(homeFor(u), { replace: true });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthShell>
      <h1>{t('auth.welcomeBack')}</h1>
      <p className="auth-sub">{t('auth.loginSub')}</p>
      <form onSubmit={submit} noValidate>
        <div className="field">
          <label>{t('auth.emailOrPhone')}</label>
          <div className="input-icon">
            <Mail size={18} />
            <input className="input" value={identifier} onChange={e => setIdentifier(e.target.value)} placeholder="email / +998 90 123 45 67" autoComplete="username" autoFocus />
          </div>
        </div>
        <div className="field has-eye">
          <label>{t('auth.password')}</label>
          <div className="input-icon">
            <Lock size={18} />
            <input className="input" type={show ? 'text' : 'password'} value={password} onChange={e => setPassword(e.target.value)} placeholder="••••••••" autoComplete="current-password" />
            <button type="button" className="eye" onClick={() => setShow(s => !s)} aria-label="toggle">{show ? <EyeOff size={18} /> : <Eye size={18} />}</button>
          </div>
        </div>
        <button className="btn btn-primary btn-block" disabled={busy} style={{ marginTop: 6, minHeight: 48 }}>
          {busy ? <Spinner size={18} /> : <LogIn size={18} />} {t('auth.login')}
        </button>
      </form>
      <p className="auth-foot">{t('auth.noAccount')} <Link to="/register"><strong>{t('auth.register')}</strong></Link></p>
    </AuthShell>
  );
}
