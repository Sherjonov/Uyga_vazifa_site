import { Skeleton } from './Loader';
import { Empty } from './Loader';

export default function DataTable({ columns, rows, loading, empty, rowKey = 'id', onRowClick }) {
  return (
    <div className="table-wrap">
      <table className="table">
        <thead>
          <tr>{columns.map(c => <th key={c.key} style={{ width: c.width, textAlign: c.align }}>{c.title}</th>)}</tr>
        </thead>
        <tbody>
          {loading &&
            Array.from({ length: 4 }).map((_, i) => (
              <tr key={i}>{columns.map(c => <td key={c.key}><Skeleton h={18} /></td>)}</tr>
            ))}
          {!loading && rows.length === 0 && (
            <tr><td colSpan={columns.length}>{empty || <Empty />}</td></tr>
          )}
          {!loading &&
            rows.map((row, idx) => (
              <tr key={row[rowKey] ?? idx} onClick={onRowClick ? () => onRowClick(row) : undefined} style={onRowClick ? { cursor: 'pointer' } : undefined}>
                {columns.map(c => (
                  <td key={c.key} style={{ textAlign: c.align }}>{c.render ? c.render(row, idx) : row[c.key]}</td>
                ))}
              </tr>
            ))}
        </tbody>
      </table>
    </div>
  );
}
