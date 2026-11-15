export default function PageHeader({ title, subtitle, actions, icon: Icon }) {
  return (
    <div className="page-header">
      <div className="row" style={{ gap: 14, flexWrap: 'nowrap' }}>
        {Icon && <div className="stat-icon"><Icon size={24} /></div>}
        <div><h1>{title}</h1>{subtitle && <p>{subtitle}</p>}</div>
      </div>
      {actions && <div className="row">{actions}</div>}
    </div>
  );
}
