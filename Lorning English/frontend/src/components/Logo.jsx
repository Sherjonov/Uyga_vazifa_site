import { Link } from 'react-router-dom';
import './Logo.css';

export default function Logo({ size = 'md', showText = true }) {
  return (
    <Link to="/" className={`logo logo-${size}`} aria-label="Learning English" style={{ textDecoration: 'none' }}>
      <span className="logo-mark">
        <svg viewBox="0 0 64 64" width="100%" height="100%"><path d="M46 16 H22 V48 H46 M22 32 H41" fill="none" stroke="#fff" strokeWidth="7" strokeLinecap="round" strokeLinejoin="round" /></svg>
      </span>
      {showText && <span className="logo-text">Learning English</span>}
    </Link>
  );
}
