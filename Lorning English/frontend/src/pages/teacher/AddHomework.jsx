import { BookPlus } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import AssignmentForm from '../../components/AssignmentForm';
import { useLang } from '../../context/LangContext';
import '../student/student.css';

export default function AddHomework() {
  const { t } = useLang();
  return <div className="page"><PageHeader icon={BookPlus} title={t('nav.addHomework')} subtitle={t('assign.homeworkSub')} /><AssignmentForm kind="homework" /></div>;
}
