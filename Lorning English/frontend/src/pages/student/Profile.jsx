import { useEffect, useState } from 'react';
import { Save, UserRound } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import { Spinner } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { initials, num } from '../../utils/format';
import './student.css';

export default function Profile() {
  const { user, setUser } = useAuth();
  const { t } = useLang();
  const toast = useToast();
  const [name, setName] = useState(user.name);
  const [bd, setBd] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    api.get('/rating/me/breakdown').then(r => setBd(r.data)).catch(() => {});
  }, []);

  const saveProfile = async e => {
    e.preventDefault();
    setBusy(true);
    try {
      const { data } = await api.put('/settings/profile', { name });
      setUser(data);
      toast.success(t('common.saved'));
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <div className="page">
      <PageHeader icon={UserRound} title={t('nav.profile')} />
      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <form className="card" onSubmit={saveProfile}>
          <div className="row" style={{ marginBottom: 20 }}>
            <div className="avatar avatar-lg">{initials(user.name)}</div>
            <div><h2>{user.name}</h2><div className="row" style={{ gap: 6 }}><span className="badge badge-primary">{t(`role.${user.role}`)}</span></div></div>
          </div>
          <div className="field"><label>{t('auth.fullName')}</label><input className="input" value={name} onChange={e => setName(e.target.value)} /></div>
          <div className="field"><label>Email</label><input className="input" value={user.email || '–'} disabled /></div>
          <div className="field"><label>{t('auth.phone')}</label><input className="input" value={user.phone || '–'} disabled /></div>
          <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner size={16} /> : <Save size={16} />} {t('common.save')}</button>
        </form>
        <div className="card">
          <div className="card-title"><h3>{t('home.scoreBreakdown')}</h3></div>
          {bd && <div className="stack" style={{ gap: 12 }}>
            <div className="row-between"><span className="text-2">{t('home.fromTests')}</span><strong className="mono">+{num(bd.tests, 1)}</strong></div>
            <div className="row-between"><span className="text-2">{t('home.fromAssignments')}</span><strong className="mono">+{num(bd.assignments, 1)}</strong></div>
            <div className="row-between"><span className="text-2">{t('home.fromGrid')}</span><strong className="mono">+{num(bd.grid, 1)}</strong></div>
            <div className="row-between"><span className="text-2">{t('home.penalties')}</span><strong className="mono" style={{ color: 'var(--danger)' }}>−{num(bd.penalties, 1)}</strong></div>
            <div className="row-between"><span className="text-2">{t('home.resubmits')}</span><strong className="mono" style={{ color: 'var(--danger)' }}>−{num(bd.resubmits, 1)}</strong></div>
            <div className="divider" style={{ margin: 0 }} />
            <div className="row-between"><strong>{t('home.total')}</strong><strong className="mono" style={{ fontSize: '1.4rem' }}>{num(bd.total, 1)}</strong></div>
          </div>}
        </div>
      </div>
    </div>
  );
}
