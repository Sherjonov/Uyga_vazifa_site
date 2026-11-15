import { Trophy } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import RatingBoard from '../../components/RatingBoard';
import { useLang } from '../../context/LangContext';

export default function Rating() {
  const { t } = useLang();
  return <div className="page"><PageHeader icon={Trophy} title={t('nav.teacherRating')} subtitle={t('rating.teacherSub')} /><RatingBoard /></div>;
}
