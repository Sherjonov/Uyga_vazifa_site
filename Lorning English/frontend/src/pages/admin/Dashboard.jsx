import { useEffect, useState } from 'react';
import { Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { Activity, BookOpenCheck, FileCheck2, Inbox, LayoutDashboard, Layers, Users, Wallet } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import { Skeleton } from '../../components/Loader';
import { fmtMoney } from '../../utils/format';
import { useLang } from '../../context/LangContext';
import api from '../../api/axios';
import './admin.css';

const COLORS = ['#5b5bf0', '#8b5cf6', '#22d3ee', '#f59e0b', '#10b981'];
const tip = { background: 'var(--surface)', border: '1px solid var(--border)', borderRadius: 12, color: 'var(--text)' };

function RevenueBlock({ s }) {
  const { t } = useLang();
  const r = s.revenue;
  const cards = [
    { label: t('billing.thisMonth'), value: r.this_month, cls: 'success' }, { label: t('billing.lastMonth'), value: r.last_month, cls: '' },
    { label: t('billing.total'), value: r.total, cls: 'info' }, { label: t('billing.pendingSum', { n: r.pending_count }), value: r.pending_amount, cls: 'warning' }
  ];
  return (
    <div style={{ marginBottom: 22 }}>
      <div className="grid grid-4 stagger" style={{ marginBottom: 18 }}>
        {cards.map(c => <div key={c.label} className="card card-hover stat"><div className={`stat-icon ${c.cls}`}><Wallet size={24} /></div><div><div className="stat-value" style={{ fontSize: '1.3rem' }}>{fmtMoney(c.value)}</div><div className="stat-label">{c.label} · {t('sub.som')}</div></div></div>)}
      </div>
      <div className="card chart-card"><div className="card-title"><h3>{t('billing.monthly')}</h3></div>
        <ResponsiveContainer width="100%" height={240}><BarChart data={r.by_month}><CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="month" stroke="var(--text-3)" fontSize={12} /><YAxis stroke="var(--text-3)" fontSize={12} tickFormatter={v => `${Math.round(v / 1000)}k`} /><Tooltip contentStyle={tip} formatter={v => `${fmtMoney(v)} ${t('sub.som')}`} /><Bar dataKey="amount" name={t('billing.income')} fill={COLORS[0]} radius={[8, 8, 0, 0]} /></BarChart></ResponsiveContainer>
      </div>
    </div>
  );
}

export default function Dashboard() {
  const { t } = useLang();
  const [s, setS] = useState(null);
  useEffect(() => { api.get('/admin/stats').then(r => setS(r.data)).catch(() => {}); }, []);

  const cards = s && [
    { icon: Users, label: t('admin.users'), value: s.users.total, sub: `${s.users.by_role.student || 0} ${t('role.student')} · ${s.users.by_role.teacher || 0} ${t('role.teacher')}`, cls: '' },
    { icon: Layers, label: t('admin.groups'), value: s.groups.total, sub: t('nav.groups'), cls: 'info' },
    { icon: Activity, label: t('admin.activeDay'), value: s.activity.daily_active, sub: `${t('admin.activeWeek')}: ${s.activity.weekly_active}`, cls: 'success' },
    { icon: FileCheck2, label: t('admin.tests'), value: s.tests.total, sub: `${s.tests.finished_attempts} ${t('admin.attempts')}`, cls: 'warning' },
    { icon: BookOpenCheck, label: t('admin.submissions'), value: s.assignments.submissions, sub: `${s.assignments.total} ${t('admin.assignments')}`, cls: 'info' },
    { icon: Inbox, label: t('admin.newTickets'), value: s.tickets.new, sub: t('nav.tickets'), cls: 'danger' }
  ];
  const series = s && s.series.map(x => ({ ...x, d: x.date.slice(5) }));

  return (
    <div className="page page-wide">
      <PageHeader icon={LayoutDashboard} title={t('nav.dashboard')} subtitle={t('admin.subtitle')} />
      <div className="grid grid-3 stagger" style={{ marginBottom: 22 }}>
        {!s ? Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} h={96} r={22} />) : cards.map(c => (
          <div key={c.label} className="card card-hover stat"><div className={`stat-icon ${c.cls}`}><c.icon size={24} /></div>
            <div><div className="stat-value">{c.value}</div><div className="stat-label">{c.label}</div><div className="hint">{c.sub}</div></div></div>
        ))}
      </div>
      {s && <RevenueBlock s={s} />}
      {s && (
        <div className="grid grid-2">
          <div className="card chart-card" style={{ gridColumn: '1 / -1' }}>
            <div className="card-title"><h3>{t('admin.activity14')}</h3></div>
            <ResponsiveContainer width="100%" height={270}>
              <AreaChart data={series}>
                <defs>{['active_users', 'submissions', 'test_attempts'].map((k, i) => <linearGradient key={k} id={`g${i}`} x1="0" y1="0" x2="0" y2="1"><stop offset="5%" stopColor={COLORS[i]} stopOpacity={0.4} /><stop offset="95%" stopColor={COLORS[i]} stopOpacity={0} /></linearGradient>)}</defs>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" /><XAxis dataKey="d" stroke="var(--text-3)" fontSize={12} /><YAxis stroke="var(--text-3)" fontSize={12} allowDecimals={false} />
                <Tooltip contentStyle={tip} /><Legend />
                <Area type="monotone" dataKey="active_users" name={t('admin.activeUsers')} stroke={COLORS[0]} fill="url(#g0)" strokeWidth={2} />
                <Area type="monotone" dataKey="submissions" name={t('admin.submissions')} stroke={COLORS[1]} fill="url(#g1)" strokeWidth={2} />
                <Area type="monotone" dataKey="test_attempts" name={t('admin.attempts')} stroke={COLORS[2]} fill="url(#g2)" strokeWidth={2} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>
      )}
    </div>
  );
}
