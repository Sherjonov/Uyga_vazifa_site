import { MessagesSquare } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DirectChat from '../../components/DirectChat';
import { useLang } from '../../context/LangContext';

export default function Messages() {
  const { t } = useLang();
  return <div className="page"><PageHeader icon={MessagesSquare} title={t('nav.messages')} subtitle={t('contact.teacherInbox')} /><DirectChat /></div>;
}
