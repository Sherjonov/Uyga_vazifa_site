import { useState } from 'react';
import { MessageCircle } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import DirectChat from '../../components/DirectChat';
import TicketBox from '../../components/TicketBox';
import { useLang } from '../../context/LangContext';

export default function ContactTeacher() {
  const { t } = useLang();
  const [tab, setTab] = useState('teacher');
  return (
    <div className="page">
      <PageHeader icon={MessageCircle} title={t('nav.contactTeacher')} subtitle={t('contact.subtitle')}
        actions={<div className="tabs">
          <button className={`tab ${tab === 'teacher' ? 'active' : ''}`} onClick={() => setTab('teacher')}>{t('contact.teacher')}</button>
          <button className={`tab ${tab === 'admin' ? 'active' : ''}`} onClick={() => setTab('admin')}>{t('contact.admin')}</button>
        </div>} />
      {tab === 'teacher' ? <DirectChat /> : <TicketBox />}
    </div>
  );
}
