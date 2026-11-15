import { useState } from 'react';
import { ChevronDown, CircleHelp } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import { useLang } from '../../context/LangContext';
import './teacher.css';

const SECTIONS = ['start', 'names', 'attendance', 'grid', 'homework', 'tests', 'retake', 'review', 'danger', 'rating', 'settings'];

/** Faqat o'qituvchi uchun: saytdan qanday foydalanish qo'llanmasi */
export default function Help() {
  const { t } = useLang();
  const [open, setOpen] = useState('start');
  return (
    <div className="page">
      <PageHeader icon={CircleHelp} title={t('nav.help')} subtitle={t('help.subtitle')} />
      <div className="alert alert-info" style={{ marginBottom: 18 }}>{t('help.intro')}</div>
      <div className="stack" style={{ gap: 10 }}>
        {SECTIONS.map((id, i) => {
          const isOpen = open === id;
          const steps = t(`help.${id}.b`).split('\n');
          return (
            <div key={id} className={`help-item card ${isOpen ? 'open' : ''}`}>
              <button className="help-head" onClick={() => setOpen(isOpen ? null : id)} aria-expanded={isOpen}>
                <span className="help-num">{i + 1}</span><strong>{t(`help.${id}.t`)}</strong><ChevronDown size={20} className="help-chev" />
              </button>
              {isOpen && <ol className="help-body">{steps.map((s, k) => <li key={k}>{s}</li>)}</ol>}
            </div>
          );
        })}
      </div>
    </div>
  );
}
