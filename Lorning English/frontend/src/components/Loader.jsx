import { Inbox } from 'lucide-react';
import './Loader.css';

export const Spinner = ({ size = 22 }) => <span className="spinner" style={{ width: size, height: size }} />;

export const PageLoader = () => (
  <div className="page-loader"><span className="spinner" style={{ width: 40, height: 40 }} /></div>
);

export const Skeleton = ({ h = 16, w = '100%', r = 10, style }) => (
  <div className="skeleton" style={{ height: h, width: w, borderRadius: r, ...style }} />
);

export const SkeletonList = ({ n = 4, h = 78 }) => (
  <div className="stack">{Array.from({ length: n }).map((_, i) => <Skeleton key={i} h={h} r={16} />)}</div>
);

export const Empty = ({ icon: Icon = Inbox, title, text, action }) => (
  <div className="empty">
    <div className="empty-icon"><Icon size={32} /></div>
    {title && <h3>{title}</h3>}
    {text && <p style={{ maxWidth: 360 }}>{text}</p>}
    {action}
  </div>
);

export default PageLoader;
