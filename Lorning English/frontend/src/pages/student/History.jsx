import { Clock3 } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import ScoreHistory from '../../components/ScoreHistory';
import { useLang } from '../../context/LangContext';
import './student.css';

export default function History() {
  const { t } = useLang();
  return (
    <div className="page">
      <PageHeader icon={Clock3} title={t('nav.scoreHistory')} subtitle={t('history.subtitle')} />
      <ScoreHistory endpoint="/rating/me/history" />
    </div>
  );
}
