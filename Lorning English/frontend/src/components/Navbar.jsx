import { Link } from 'react-router-dom';
import { Crown, Menu, Star } from 'lucide-react';
import LangSwitcher from './LangSwitcher';
import ThemeToggle from './ThemeToggle';
import { useAuth } from '../context/AuthContext';
import { useLang } from '../context/LangContext';
import { initials, num } from '../utils/format';
import './Navbar.css';

export default function Navbar({ menuOpen, onMenu }) {
  const { user } = useAuth();
  const { t } = useLang();
  return (
    <header className={`navbar ${menuOpen ? 'menu-open' : ''}`}>
      <button
        type="button"
        className="btn btn-ghost btn-icon nav-burger"
        onClick={onMenu}
        aria-label={menuOpen ? 'Close navigation menu' : 'Open navigation menu'}
        aria-expanded={menuOpen}
        aria-controls="app-sidebar"
      >
        <Menu size={20} />
      </button>
      <div className="spacer" />
      {user.role === 'student' && (
        <span className="score-chip" title={t('nav.myScore')}><Star size={15} fill="currentColor" />{num(user.total_score, 1)}</span>
      )}
      {user.role === 'teacher' && user.subscription?.until && (() => {
        const days = Math.ceil((new Date(user.subscription.until) - Date.now()) / 86400000);
        if (!user.subscription.trial && days > 7) return null;
        return <Link to="/teacher/subscription" className={`score-chip sub-chip ${days <= 3 ? 'danger' : ''}`}><Crown size={14} />{days <= 0 ? t('sub.expiredShort') : t(user.subscription.trial ? 'sub.chipTrial' : 'sub.chipDays', { n: days })}</Link>;
      })()}
      <LangSwitcher />
      <ThemeToggle />
      <div className="avatar nav-avatar" title={user.name}>{initials(user.name)}</div>
    </header>
  );
}
