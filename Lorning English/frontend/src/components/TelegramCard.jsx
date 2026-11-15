import { useEffect, useState } from 'react';
import { ExternalLink, Unlink } from 'lucide-react';
import { Spinner } from './Loader';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';

/** O'quvchi: saytdagi hisobni Telegram botga ulash (vazifa baholari, natijalar, tasdiqlash kodi) */
export default function TelegramCard() {
  const { t } = useLang();
  const toast = useToast();
  const [st, setSt] = useState(null);
  const [busy, setBusy] = useState(false);

  const load = () => api.get('/telegram/me').then(r => setSt(r.data)).catch(() => setSt({ enabled: false }));
  useEffect(() => { load(); }, []);

  const connect = async () => {
    setBusy(true);
    try {
      const { data } = await api.post('/telegram/link-token');
      window.open(data.url, '_blank', 'noopener');
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };
  const unlink = async () => {
    try { await api.delete('/telegram/me'); toast.success(t('tg.unlinked')); load(); } catch (err) { toast.error(errMsg(err)); }
  };

  return (
    <section className="card stack" style={{ gap: 12 }}>
      <h3>✈️ {t('tg.title')}</h3>
      {st === null ? <Spinner size={22} /> : !st.enabled ? <p className="muted">{t('tg.off')}</p> : (
        <>
          <p className="text-2" style={{ margin: 0 }}>{t('tg.text')}</p>
          {st.linked ? (
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <span className="badge badge-success">✅ {t('tg.linked')}{st.username ? ` · @${st.username}` : ''}</span>
              <button className="btn btn-ghost btn-sm" onClick={unlink}><Unlink size={14} /> {t('tg.unlink')}</button>
            </div>
          ) : (
            <div className="row">
              <button className="btn btn-primary" onClick={connect} disabled={busy}>{busy ? <Spinner size={16} /> : <ExternalLink size={16} />} {t('tg.connect')}</button>
              <span className="hint">{t('tg.connectHint')}</span>
            </div>
          )}
          <p className="hint" style={{ margin: 0 }}>{t('tg.parentHint')}</p>
        </>
      )}
    </section>
  );
}
