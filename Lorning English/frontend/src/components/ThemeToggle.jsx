import { Moon, Sun } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';
import './ThemeToggle.css';

export default function ThemeToggle() {
  const { theme, toggle } = useTheme();
  return (
    <button className={`theme-toggle ${theme}`} onClick={toggle} aria-label="theme" title={theme === 'dark' ? 'Light' : 'Dark'}>
      <span className="theme-knob">{theme === 'dark' ? <Moon size={15} /> : <Sun size={15} />}</span>
    </button>
  );
}
