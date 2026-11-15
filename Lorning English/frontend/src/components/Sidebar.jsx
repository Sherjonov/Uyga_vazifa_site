import { NavLink } from 'react-router-dom';
import {
  Home, BookOpenCheck, FileCheck2, Trophy, Sparkles, UserRound, Settings, MessageCircle,
  Users, Table2, ShieldAlert, BookPlus, FilePlus2, CheckCheck, MessagesSquare, History,
  X, LogOut, CircleHelp, Library, BookA, ListChecks, Sparkle, RotateCcw
} from 'lucide-react';
import Logo from './Logo';
import { useAuth } from '../context/AuthContext';
import { useLang } from '../context/LangContext';
import { initials } from '../utils/format';
import './Sidebar.css';

const MENUS = {
  student: [
    { to: '/student/home', icon: Home, key: 'nav.home' },
    { to: '/student/homework', icon: BookOpenCheck, key: 'nav.homework' },
    { to: '/student/vocab', icon: BookA, key: 'nav.vocab' },
    { to: '/student/books', icon: Library, key: 'nav.books' },
    { to: '/student/extra', icon: Sparkle, key: 'nav.extra' },
    { to: '/student/tests', icon: FileCheck2, key: 'nav.tests' },
    { to: '/student/rating', icon: Trophy, key: 'nav.rating' },
    { to: '/student/history', icon: History, key: 'nav.scoreHistory' },
    { to: '/student/uztoz-ai', icon: Sparkles, key: 'nav.uztozAi', accent: true },
    { to: '/student/profile', icon: UserRound, key: 'nav.profile' },
    { to: '/student/settings', icon: Settings, key: 'nav.settings' },
    { to: '/student/contact', icon: MessageCircle, key: 'nav.contactTeacher' }
  ],
  teacher: [
    { to: '/teacher/students', icon: Users, key: 'nav.students' },
    { to: '/teacher/grid', icon: Table2, key: 'nav.grid' },
    { to: '/teacher/danger-zone', icon: ShieldAlert, key: 'nav.dangerZone' },
    { to: '/teacher/homework', icon: BookPlus, key: 'nav.addHomework' },
    { to: '/teacher/extra', icon: Sparkle, key: 'nav.addExtra' },
    { to: '/teacher/books', icon: Library, key: 'nav.books' },
    { to: '/teacher/vocab-results', icon: ListChecks, key: 'nav.vocabResults' },
    { to: '/teacher/retake', icon: RotateCcw, key: 'nav.retake' },
    { to: '/teacher/tests', icon: FilePlus2, key: 'nav.addTest' },
    { to: '/teacher/review', icon: CheckCheck, key: 'nav.review' },
    { to: '/teacher/rating', icon: Trophy, key: 'nav.teacherRating' },
    { to: '/teacher/messages', icon: MessagesSquare, key: 'nav.messages' },
    { to: '/teacher/help', icon: CircleHelp, key: 'nav.help' },
    { to: '/teacher/settings', icon: Settings, key: 'nav.settings' }
  ]
};

export default function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth();
  const { t } = useLang();
  const items = MENUS[user.role] || [];

  return (
    <>
      <div className={`sidebar-overlay ${open ? 'show' : ''}`} onClick={onClose} />
      <aside id="app-sidebar" className={`sidebar ${open ? 'open' : ''}`}>
        <div className="sidebar-head">
          <Logo />
          <button
            type="button"
            className="btn btn-ghost btn-icon btn-sm sidebar-close"
            onClick={onClose}
            aria-label="Close navigation menu"
          >
            <X size={18} />
          </button>
        </div>
        <nav className="sidebar-nav">
          {items.map(({ to, icon: Icon, key, accent }) => (
            <NavLink key={to} to={to} onClick={onClose} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''} ${accent ? 'accent' : ''}`}>
              <Icon size={19} />
              <span>{t(key)}</span>
            </NavLink>
          ))}
        </nav>
        <div className="sidebar-foot">
          <div className="avatar">{initials(user.name)}</div>
          <div className="sidebar-user">
            <strong>{user.name}</strong>
            <span>{t(`role.${user.role}`)}</span>
          </div>
          <button className="btn btn-ghost btn-icon btn-sm" onClick={logout} title={t('auth.logout')} aria-label="logout"><LogOut size={17} /></button>
        </div>
      </aside>
    </>
  );
}
