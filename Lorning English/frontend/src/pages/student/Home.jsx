import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { BookOpenCheck, CalendarCheck, FileCheck2, Sparkles, Star, Trophy, UsersRound } from 'lucide-react';
import { Skeleton } from '../../components/Loader';
import { useAuth } from '../../context/AuthContext';
import { useLang } from '../../context/LangContext';
import api from '../../api/axios';
import { fmtDateTime, num } from '../../utils/format';
import './student.css';

export default function Home() {
  const { user, setUser } = useAuth();
  const { t, lang } = useLang();
  const [d, setD] = useState(null);

  useEffect(() => {
    const safe = p => p.then(r => r.data).catch(() => null);
    Promise.all([
      safe(api.get('/rating', { params: { scope: 'all' } })),
      safe(api.get('/rating/me/breakdown')),
      safe(api.get('/assignments/mine', { params: { kind: 'homework', status: 'pending' } })),
      safe(api.get('/tests/mine')),
      safe(api.get('/attendance/me')),
      safe(api.get('/groups'))
    ]).then(([rating, breakdown, hw, tests, att, groups]) => {
      if (breakdown) setUser(current => current ? { ...current, total_score: breakdown.total } : current);
      setD({ rating, breakdown, hw: hw || [], tests: tests || [], att, groups: groups || [] });
    });
  }, []);

  const stats = d && [
    { icon: Star, cls: 'warning', value: num(d.breakdown?.total ?? user.total_score, 1), label: t('home.score') },
    { icon: Trophy, cls: '', value: d.rating?.me ? `#${d.rating.me.rank}` : '–', label: t('home.rank') },
    { icon: BookOpenCheck, cls: 'info', value: d.hw.length, label: t('home.pendingHomework') },
    { icon: FileCheck2, cls: 'success', value: d.tests.filter(x => x.state === 'available' || x.state === 'in_progress' || x.state === 'retake_approved').length, label: t('home.openTests') }
  ];
  const upcoming = d ? d.hw.filter(h => h.due_at).slice(0, 4) : [];

  return (
    <div className="page">
      <div className="hello anim-scale-in" style={{ marginBottom: 24 }}>
        <h1>{t('home.hello', { name: user.name.split(' ')[0] })} 👋</h1>
        <p>{t('home.subtitle')}</p>
        <Link to="/student/uztoz-ai" className="btn"><Sparkles size={17} /> {t('home.askAi')}</Link>
      </div>

      {d && d.groups.length === 0 && (
        <Link to="/join" className="card card-hover row" style={{ textDecoration: 'none', color: 'inherit', marginBottom: 24, borderColor: 'var(--primary)' }}>
          <div className="stat-icon"><UsersRound size={22} /></div>
          <div className="spacer"><strong>{t('home.noGroup')}</strong><div className="hint">{t('home.noGroupText')}</div></div>
          <span className="btn btn-primary btn-sm">{t('home.joinGroup')}</span>
        </Link>
      )}


      <div className="grid grid-4 stagger" style={{ marginBottom: 24 }}>
        {!d ? Array.from({ length: 4 }).map((_, i) => <Skeleton key={i} h={92} r={22} />) : stats.map(s => (
          <div key={s.label} className="card card-hover stat">
            <div className={`stat-icon ${s.cls}`}><s.icon size={24} /></div>
            <div><div className="stat-value">{s.value}</div><div className="stat-label">{s.label}</div></div>
          </div>
        ))}
      </div>

      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <div className="card">
          <div className="card-title"><h3>{t('home.deadlines')}</h3><Link to="/student/homework">{t('common.all')}</Link></div>
          {!d ? <Skeleton h={120} /> : upcoming.length === 0 ? <p className="muted">{t('home.noDeadlines')}</p> : (
            <div className="stack" style={{ gap: 10 }}>
              {upcoming.map(h => (
                <div key={h.id} className="list-item">
                  <div className="stat-icon info" style={{ width: 40, height: 40 }}><BookOpenCheck size={19} /></div>
                  <div className="spacer"><strong>{h.title}</strong><div className="hint">{fmtDateTime(h.due_at, lang)}</div></div>
                  {h.overdue && <span className="badge badge-danger">{t('assign.overdue')}</span>}
                </div>
              ))}
            </div>
          )}
        </div>
        <div className="stack">
          <div className="card">
            <div className="card-title"><h3>{t('home.scoreBreakdown')}</h3></div>
            {!d?.breakdown ? <Skeleton h={90} /> : (
              <div className="stack" style={{ gap: 10 }}>
                <div className="row-between"><span className="text-2">{t('home.fromTests')}</span><strong className="mono">+{num(d.breakdown.tests, 1)}</strong></div>
                <div className="row-between"><span className="text-2">{t('home.fromAssignments')}</span><strong className="mono">+{num(d.breakdown.assignments, 1)}</strong></div>
                <div className="row-between"><span className="text-2">{t('home.fromGrid')}</span><strong className="mono">+{num(d.breakdown.grid, 1)}</strong></div>
                <div className="row-between"><span className="text-2">{t('home.penalties')}</span><strong className="mono" style={{ color: 'var(--danger)' }}>−{num(d.breakdown.penalties, 1)}</strong></div>
                <div className="row-between"><span className="text-2">{t('home.resubmits')}</span><strong className="mono" style={{ color: 'var(--danger)' }}>−{num(d.breakdown.resubmits, 1)}</strong></div>
                <div className="divider" style={{ margin: '4px 0' }} />
                <div className="row-between"><strong>{t('home.total')}</strong><strong className="mono" style={{ fontSize: '1.2rem' }}>{num(d.breakdown.total, 1)}</strong></div>
              </div>
            )}
          </div>
          <div className="card">
            <div className="card-title"><h3>{t('home.attendance')}</h3><CalendarCheck size={20} className="muted" /></div>
            {!d?.att ? <Skeleton h={50} /> : (
              <div className="row">
                <span className="badge badge-success">{t('att.present')}: {d.att.totals.present || 0}</span>
                <span className="badge badge-danger">{t('att.absent')}: {d.att.totals.absent || 0}</span>
                <span className="badge badge-warning">{t('att.late')}: {d.att.totals.late || 0}</span>
                <span className="badge badge-warning">{t('att.excused')}: {d.att.totals.excused || 0}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
