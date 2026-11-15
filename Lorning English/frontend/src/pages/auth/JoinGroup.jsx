import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Check, GraduationCap, Search, UserCheck } from 'lucide-react';
import Logo from '../../components/Logo';
import LangSwitcher from '../../components/LangSwitcher';
import ThemeToggle from '../../components/ThemeToggle';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import '../../components/AuthShell.css';
import './Onboarding.css';
import './JoinGroup.css';

/** O'quvchi: guruhini tanlaydi va faqat o'qituvchi ro'yxatga kiritgan ismlar ichidan o'zini topadi */
export default function JoinGroup() {
  const { t } = useLang();
  const { setUser } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [groups, setGroups] = useState(null);
  const [group, setGroup] = useState(null);
  const [q, setQ] = useState('');
  const [names, setNames] = useState(null);
  const [pick, setPick] = useState(null);
  const [busy, setBusy] = useState(false);

  useEffect(() => { api.get('/roster/groups').then(r => setGroups(r.data)).catch(() => setGroups([])); }, []);

  useEffect(() => {
    if (!group) return undefined;
    setNames(null);
    const id = setTimeout(() => {
      api.get(`/roster/groups/${group.id}/names`, { params: q.trim() ? { q: q.trim() } : {} }).then(r => setNames(r.data)).catch(() => setNames([]));
    }, 250);
    return () => clearTimeout(id);
  }, [group, q]);

  const claim = async () => {
    setBusy(true);
    try {
      const { data } = await api.post('/roster/claim', { student_id: pick.id });
      setUser(data.user);
      toast.success(t('join.success', { name: data.user.name, group: data.group.name }));
      nav('/student/home', { replace: true });
    } catch (err) {
      toast.error(errMsg(err));
      setPick(null);
      setQ(x => x + ' ');
      setTimeout(() => setQ(x => x.trim()), 0);
    } finally { setBusy(false); }
  };

  return (
    <div className="onb">
      <div className="auth-blob b1" style={{ position: 'absolute' }} /><div className="auth-blob b2" style={{ position: 'absolute' }} />
      <div className="onb-top"><Logo /><div className="row"><LangSwitcher /><ThemeToggle /></div></div>
      <div className="onb-body join">
        <div className="onb-steps"><span className="on" /><span className="on" /><span className="on" /></div>
        <div className="join-card-box">
          <h1>{t('join.title')}</h1>
          <p className="auth-sub">{t('join.subtitle')}</p>

          {groups === null ? <SkeletonList n={2} h={80} /> : groups.length === 0 ? (
            <Empty icon={GraduationCap} title={t('join.noGroups')} text={t('join.noGroupsText')} />
          ) : (
            <div className="join-groups">
              {groups.map(g => (
                <button key={g.id} className={`join-group ${group?.id === g.id ? 'selected' : ''}`} onClick={() => { setGroup(g); setPick(null); setQ(''); }}>
                  <strong>{g.name}</strong>
                  <span>{g.teacher_name}</span>
                  <em>{t('join.freeNames', { n: g.free_count })}</em>
                </button>
              ))}
            </div>
          )}

          {group && (
            <div className="join-names anim-fade-up">
              <label className="label">{t('join.searchLabel')}</label>
              <div className="input-icon" style={{ position: 'relative' }}>
                <Search size={18} style={{ position: 'absolute', left: 14, top: 13, color: 'var(--text-3)' }} />
                <input className="input" style={{ paddingLeft: 44 }} value={q} onChange={e => setQ(e.target.value)} placeholder={t('common.search')} autoFocus />
              </div>
              <div className="join-list">
                {names === null ? <div className="center" style={{ padding: 24 }}><Spinner /></div> : names.length === 0 ? (
                  <div className="join-empty"><strong>{t('join.notFound')}</strong><span>{t('join.hint')}</span></div>
                ) : names.map(n => (
                  <button key={n.id} className={`join-name ${pick?.id === n.id ? 'selected' : ''}`} onClick={() => setPick(n)}>
                    <span className="avatar">{n.name.slice(0, 1).toUpperCase()}</span><span className="spacer">{n.name}</span>{pick?.id === n.id && <Check size={18} />}
                  </button>
                ))}
              </div>
              <button className="btn btn-primary btn-block" style={{ minHeight: 50, marginTop: 14 }} disabled={!pick || busy} onClick={claim}>
                {busy ? <Spinner size={18} /> : <UserCheck size={18} />} {pick ? t('join.confirm', { name: pick.name }) : t('join.pickName')}
              </button>
            </div>
          )}

          <p className="join-hint">{t('join.hint')}</p>
          <button className="link-btn" style={{ display: 'block', margin: '6px auto 0' }} onClick={() => nav('/student/home', { replace: true })}>{t('join.later')}</button>
        </div>
      </div>
    </div>
  );
}
