import { useMemo } from 'react';
import ElectricLogo from './ElectricLogo';
import LangSwitcher from './LangSwitcher';
import ThemeToggle from './ThemeToggle';
import Logo from './Logo';
import { useTheme } from '../context/ThemeContext';
import { useLang } from '../context/LangContext';
import './AuthShell.css';

const hasWebGL2 = () => {
  try {
    const c = document.createElement('canvas');
    const gl = c.getContext('webgl2');
    gl?.getExtension('WEBGL_lose_context')?.loseContext();
    return !!gl;
  } catch {
    return false;
  }
};

/** Kirish/ro'yxatdan o'tish sahifalari uchun umumiy qobiq: chapda animatsiyali Learning English logotipi, o'ngda forma kartasi */
export default function AuthShell({ children }) {
  const { theme } = useTheme();
  const { t } = useLang();
  const webgl = useMemo(hasWebGL2, []);

  return (
    <div className="auth">
      <div className="auth-blob b1" /><div className="auth-blob b2" /><div className="auth-blob b3" />
      <div className="auth-top">
        <span className="auth-top-logo"><Logo /></span>
        <div className="row"><LangSwitcher /><ThemeToggle /></div>
      </div>
      <div className="auth-grid">
        <section className="auth-hero">
          <div style={{ width: '100%', height: '480px', position: 'relative' }}>
            {webgl ? (
              <ElectricLogo
                src="/logo.svg"
                color="#ecc7ff"
                glowColor="#1624b8"
                scale={0.7}
                strands={4}
                bend={0.6}
                crackle={1.5}
                arcs={1}
                speed={2.5}
                interactive
                intensity={1}
                glow={1}
                thickness={1.5}
                flicker={0.6}
                fill={0}
                cursorIntensity={0.75}
                cursorRadius={100}
                theme={theme}
              />
            ) : (
              <div className="hero-fallback">Learning English</div>
            )}
          </div>
          <h2 className="hero-title">{t('auth.heroTitle')}</h2>
          <p className="hero-text">{t('auth.heroText')}</p>
          <div className="hero-tags"><span>Grammar</span><span>Vocabulary</span><span>Speaking</span><span>Ustoz AI</span></div>
        </section>
        <section className="auth-card-wrap">
          <div className="auth-card">{children}</div>
        </section>
      </div>
    </div>
  );
}
