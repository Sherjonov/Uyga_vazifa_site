import { useState } from 'react';
import { KeyRound } from 'lucide-react';
import { Spinner } from './Loader';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';

export default function PasswordForm() {
  const { t } = useLang();
  const toast = useToast();
  const [f, setF] = useState({ old: '', next: '', again: '' });
  const [busy, setBusy] = useState(false);
  const set = k => e => setF({ ...f, [k]: e.target.value });

  const submit = async e => {
    e.preventDefault();
    if (f.next.length < 6) return toast.error(t('err.passwordShort'));
    if (f.next !== f.again) return toast.error(t('err.passwordMismatch'));
    setBusy(true);
    try {
      await api.put('/settings/password', { old_password: f.old, new_password: f.next });
      toast.success(t('settings.passwordChanged'));
      setF({ old: '', next: '', again: '' });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="card" onSubmit={submit}>
      <div className="card-title"><h3>{t('settings.changePassword')}</h3><KeyRound size={20} className="muted" /></div>
      <div className="field"><label>{t('settings.oldPassword')}</label><input className="input" type="password" value={f.old} onChange={set('old')} autoComplete="current-password" /></div>
      <div className="field"><label>{t('settings.newPassword')}</label><input className="input" type="password" value={f.next} onChange={set('next')} autoComplete="new-password" /></div>
      <div className="field"><label>{t('settings.confirmPassword')}</label><input className="input" type="password" value={f.again} onChange={set('again')} autoComplete="new-password" /></div>
      <button className="btn btn-primary" disabled={busy}>{busy && <Spinner size={16} />} {t('common.save')}</button>
    </form>
  );
}
