import { Menu, Star } from 'lucide-react';
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
      <LangSwitcher />
      <ThemeToggle />
      <div className="avatar nav-avatar" title={user.name}>{initials(user.name)}</div>
    </header>
  );
}
