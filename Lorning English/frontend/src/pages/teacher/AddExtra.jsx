import { Sparkle } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import AssignmentForm from '../../components/AssignmentForm';
import { useLang } from '../../context/LangContext';
import '../student/student.css';

export default function AddExtra() {
  const { t } = useLang();
  return <div className="page"><PageHeader icon={Sparkle} title={t('nav.addExtra')} subtitle={t('extra.sub')} /><AssignmentForm kind="extra" /></div>;
}
