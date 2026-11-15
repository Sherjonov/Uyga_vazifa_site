import { Settings as Cog } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import PasswordForm from '../../components/PasswordForm';
import PreferencesCard from '../../components/PreferencesCard';
import { useLang } from '../../context/LangContext';

export default function Settings() {
  const { t } = useLang();
  return (
    <div className="page">
      <PageHeader icon={Cog} title={t('nav.settings')} subtitle={t('settings.subtitle')} />
      <div className="grid grid-2" style={{ alignItems: 'start' }}><PasswordForm /><PreferencesCard /></div>
    </div>
  );
}
