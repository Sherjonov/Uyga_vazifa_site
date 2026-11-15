import { useCallback, useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';
import {
  Home, BookOpenCheck, FileCheck2, Trophy, Sparkles, UserRound, Settings, MessageCircle,
  Users, Table2, ShieldAlert, BookPlus, FilePlus2, CheckCheck, MessagesSquare, History,
  PhoneCall, X, LogOut, CircleHelp, Library, BookA, ListChecks, Sparkle, RotateCcw
} from 'lucide-react';
import Logo from './Logo';
import api from '../api/axios';
import { useAuth } from '../context/AuthContext';
import { useLang } from '../context/LangContext';
import { initials } from '../utils/format';
import './Sidebar.css';

const MENUS = {
  student: [
    { to: '/student/home', icon: Home, key: 'nav.home' },
    { to: '/student/homework', badge: 'homework', icon: BookOpenCheck, key: 'nav.homework' },
    { to: '/student/vocab', icon: BookA, key: 'nav.vocab' },
    { to: '/student/books', badge: 'books', seen: 'books', icon: Library, key: 'nav.books' },
    { to: '/student/extra', badge: 'extra', icon: Sparkle, key: 'nav.extra' },
    { to: '/student/tests', badge: 'tests', icon: FileCheck2, key: 'nav.tests' },
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
    { to: '/teacher/vocab-results', badge: 'vocab', seen: 'vocab', icon: ListChecks, key: 'nav.vocabResults' },
    { to: '/teacher/retake', badge: 'retake', icon: RotateCcw, key: 'nav.retake' },
    { to: '/teacher/tests', icon: FilePlus2, key: 'nav.addTest' },
    { to: '/teacher/review', badge: 'review', icon: CheckCheck, key: 'nav.review' },
    { to: '/teacher/rating', icon: Trophy, key: 'nav.teacherRating' },
    { to: '/teacher/messages', badge: 'messages', icon: MessagesSquare, key: 'nav.messages' },
    { to: '/teacher/parents', icon: PhoneCall, key: 'nav.parents' },
    { to: '/teacher/help', icon: CircleHelp, key: 'nav.help' },
    { to: '/teacher/settings', icon: Settings, key: 'nav.settings' }
  ]
};

const seenKey = name => `aedu_seen_${name}`;
const readSeen = name => { try { return localStorage.getItem(seenKey(name)) || undefined; } catch { return undefined; } };
const writeSeen = (name, value) => { try { localStorage.setItem(seenKey(name), value); } catch { /* ruxsat yo'q */ } };

/** Yon menyudagi son: kutilayotgan ishlar / yangi kelganlar */
function useBadges(role, pathname) {
  const [counts, setCounts] = useState({});
  const load = useCallback(() => {
    if (role !== 'student' && role !== 'teacher') return;
    api.get('/badges', { params: { books_since: readSeen('books'), vocab_since: readSeen('vocab') } })
      .then(({ data }) => {
        const next = { ...data };
        // Hozir shu bo'limda bo'lsa, "yangi" deb hisoblanmaydi
        for (const item of MENUS[role]) {
          if (item.seen && pathname.startsWith(item.to)) { writeSeen(item.seen, data.now); next[item.badge] = 0; }
        }
        setCounts(next);
      })
      .catch(() => {});
  }, [role, pathname]);
  useEffect(() => {
    load();
    const timer = setInterval(load, 30000);
    return () => clearInterval(timer);
  }, [load]);
  return counts;
}

export default function Sidebar({ open, onClose }) {
  const { user, logout } = useAuth();
  const { t } = useLang();
  const items = MENUS[user.role] || [];
  const { pathname } = useLocation();
  const counts = useBadges(user.role, pathname);

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
          {items.map(({ to, icon: Icon, key, accent, badge }) => (
            <NavLink key={to} to={to} onClick={onClose} className={({ isActive }) => `nav-item ${isActive ? 'active' : ''} ${accent ? 'accent' : ''}`}>
              <Icon size={19} />
              <span>{t(key)}</span>
              {badge && counts[badge] > 0 && <span className="nav-badge">{counts[badge] > 99 ? '99+' : counts[badge]}</span>}
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
