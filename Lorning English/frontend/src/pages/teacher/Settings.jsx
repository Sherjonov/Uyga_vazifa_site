import { useEffect, useState } from 'react';
import { Save, Settings as Cog } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import PasswordForm from '../../components/PasswordForm';
import PreferencesCard from '../../components/PreferencesCard';
import { Skeleton, Spinner } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';

const FIELDS = [
  ['absence_penalty', 'tset.penalty', 'tset.penaltyHint', 0.5],
  ['late_penalty', 'tset.latePenalty', 'tset.latePenaltyHint', 0.5],
  ['hw_late_penalty', 'tset.hwLate', 'tset.hwLateHint', 0.5],
  ['hw_missing_penalty', 'tset.hwMissing', 'tset.hwMissingHint', 0.5],
  ['grid_max_score', 'tset.gridMax', 'tset.gridMaxHint', 1],
  ['ai_daily_limit', 'tset.aiLimit', 'tset.aiLimitHint', 1],
  ['similarity_threshold', 'tset.similarity', 'tset.similarityHint', 1],
  ['vocab_warning_limit', 'tset.vocabWarn', 'tset.vocabWarnHint', 1],
  ['vocab_pass_percent', 'tset.vocabPass', 'tset.vocabPassHint', 1],
  ['danger_missed_homework', 'tset.missedHw', 'tset.missedHwHint', 1],
  ['danger_low_test_score', 'tset.lowTest', 'tset.lowTestHint', 0.5],
  ['danger_absences', 'tset.absences', 'tset.absencesHint', 1],
  ['danger_score_drop', 'tset.scoreDrop', 'tset.scoreDropHint', 1],
  ['danger_inactive_days', 'tset.inactive', 'tset.inactiveHint', 1]
];

export default function Settings() {
  const { t } = useLang();
  const toast = useToast();
  const [f, setF] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { api.get('/settings/teacher').then(r => setF(r.data)).catch(err => toast.error(errMsg(err))); }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const save = async e => {
    e.preventDefault();
    setBusy(true);
    try {
      const body = Object.fromEntries(Object.entries(f).map(([k, v]) => [k, Number(v)]));
      setF((await api.put('/settings/teacher', body)).data);
      toast.success(t('common.saved'));
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <div className="page">
      <PageHeader icon={Cog} title={t('nav.settings')} subtitle={t('settings.subtitle')} />
      <div className="grid grid-2" style={{ alignItems: 'start' }}>
        <form className="card" onSubmit={save}>
          <div className="card-title"><h3>{t('tset.title')}</h3></div>
          {!f ? <Skeleton h={260} /> : <>
            {FIELDS.map(([k, label, hint, step]) => (
              <div className="field" key={k}><label>{t(label)}</label><input className="input" type="number" step={step} min={0} value={f[k]} onChange={e => setF({ ...f, [k]: e.target.value })} /><span className="hint">{t(hint)}</span></div>
            ))}
            <button className="btn btn-primary" disabled={busy}>{busy ? <Spinner size={16} /> : <Save size={16} />} {t('common.save')}</button>
          </>}
        </form>
        <div className="stack"><PasswordForm /><PreferencesCard /></div>
      </div>
    </div>
  );
}
