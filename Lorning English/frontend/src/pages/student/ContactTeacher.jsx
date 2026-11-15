import { MessageCircle } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DirectChat from '../../components/DirectChat';
import { useLang } from '../../context/LangContext';

export default function ContactTeacher() {
  const { t } = useLang();
  return (
    <div className="page">
      <PageHeader icon={MessageCircle} title={t('nav.contactTeacher')} subtitle={t('contact.subtitle')} />
      <DirectChat />
    </div>
  );
}
