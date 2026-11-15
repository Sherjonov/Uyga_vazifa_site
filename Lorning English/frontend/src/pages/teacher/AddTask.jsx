import { ClipboardPlus } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import AssignmentForm from '../../components/AssignmentForm';
import { useLang } from '../../context/LangContext';
import '../student/student.css';

export default function AddTask() {
  const { t } = useLang();
  return <div className="page"><PageHeader icon={ClipboardPlus} title={t('nav.addTask')} subtitle={t('assign.taskSub')} /><AssignmentForm kind="task" /></div>;
}
