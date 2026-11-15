import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { BookOpen, Presentation, UserRound } from 'lucide-react';
import ElectricLogoMini from '../../components/Logo';
import LangSwitcher from '../../components/LangSwitcher';
import ThemeToggle from '../../components/ThemeToggle';
import { Spinner } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { homeFor } from '../../utils/format';
import '../../components/AuthShell.css';
import './Onboarding.css';

const TRACK = 'english'; // platforma faqat ingliz tili uchun

export default function Onboarding() {
  const { t } = useLang();
  const { setUser } = useAuth();
  const toast = useToast();
  const nav = useNavigate();
  const [role, setRole] = useState(null);
  const [busy, setBusy] = useState(false);

  const finish = async () => {
    setBusy(true);
    try {
      const { data } = await api.post('/onboarding', { track: TRACK, role });
      setUser(data);
      nav(data.role === 'student' ? '/join' : homeFor(data), { replace: true });
    } catch (err) {
      toast.error(errMsg(err));
    } finally {
      setBusy(false);
    }
  };

  const roles = [
    { id: 'student', icon: UserRound, label: t('onb.student'), desc: t('onb.studentDesc') },
    { id: 'teacher', icon: Presentation, label: t('onb.teacher'), desc: t('onb.teacherDesc') }
  ];

  return (
    <div className="onb">
      <div className="auth-blob b1" style={{ position: 'absolute' }} />
      <div className="onb-top"><ElectricLogoMini /><div className="row"><LangSwitcher /><ThemeToggle /></div></div>
      <div className="onb-body">
        <div className="onb-step" key="s2">
          <h1>{t('onb.step2Title')}</h1>
          <p className="auth-sub">{t('onb.step2Sub')}</p>
          <div className="onb-cards two">
            {roles.map(({ id, icon: Icon, label, desc }) => (
              <button key={id} className={`onb-card ${role === id ? 'selected' : ''}`} style={{ '--c': id === 'student' ? '#5b5bf0' : '#8b5cf6' }} onClick={() => setRole(id)}>
                <span className="onb-ico"><Icon size={36} /></span>
                <strong>{label}</strong>
                <span>{desc}</span>
              </button>
            ))}
          </div>
          <div className="onb-actions">
            <button className="btn btn-primary" disabled={!role || busy} onClick={finish} style={{ minHeight: 48, minWidth: 180 }}>
              {busy ? <Spinner size={18} /> : <BookOpen size={18} />} {t('onb.start')}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
