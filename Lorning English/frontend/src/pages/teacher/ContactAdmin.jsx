import { LifeBuoy } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import TicketBox from '../../components/TicketBox';
import { useLang } from '../../context/LangContext';

export default function ContactAdmin() {
  const { t } = useLang();
  return <div className="page"><PageHeader icon={LifeBuoy} title={t('nav.contactAdmin')} subtitle={t('ticket.subtitle')} /><TicketBox /></div>;
}
