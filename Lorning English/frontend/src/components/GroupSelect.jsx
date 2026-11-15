import './GroupSelect.css';

/** Guruhlar orasida tezkor almashtirgich: kam bo'lsa tablar, ko'p bo'lsa dropdown */
export default function GroupSelect({ groups, value, onChange, all = false, allLabel = '' }) {
  if (!groups.length) return null;
  if (groups.length <= 5 && !all) {
    return (
      <div className="tabs group-tabs">
        {groups.map(g => (
          <button key={g.id} className={`tab ${g.id === value ? 'active' : ''}`} onClick={() => onChange(g.id)}>{g.name}</button>
        ))}
      </div>
    );
  }
  return (
    <select className="select group-select" value={value ?? ''} onChange={e => onChange(e.target.value ? Number(e.target.value) : null)}>
      {all && <option value="">{allLabel}</option>}
      {groups.map(g => <option key={g.id} value={g.id}>{g.name}</option>)}
    </select>
  );
}
