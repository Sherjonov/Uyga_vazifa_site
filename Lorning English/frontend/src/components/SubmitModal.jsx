import { useEffect, useMemo, useRef, useState } from 'react';
import { FileText, Send, UploadCloud, X } from 'lucide-react';
import Modal from './Modal';
import FileChips from './FileChips';
import { Spinner } from './Loader';
import { useLang } from '../context/LangContext';
import { useToast } from './Toast';
import api, { errMsg } from '../api/axios';
import './SubmitModal.css';

const ACCEPT = '.py,.zip,.jpg,.jpeg,.png,.webp,.pdf,.txt,.html,.css,.js,.doc,.docx,.xls,.xlsx,.ppt,.pptx';
const MAX_FILES = 10;

/** Vazifani matn, kod, rasm yoki fayl bilan topshirish. Qayta yuborilsa ball ayiriladi va ish yangidan tekshiriladi. */
export default function SubmitModal({ assignment, onClose, onDone }) {
  const { t } = useLang();
  const toast = useToast();
  const a = assignment;
  const editing = !!a?.submission?.submitted_at;
  const penalty = a?.resubmit_penalty ?? 3;
  const [text, setText] = useState(a?.submission?.text || '');
  const [files, setFiles] = useState([]);
  const [honest, setHonest] = useState(false);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const input = useRef(null);
  const existing = a?.submission?.files || [];

  const previews = useMemo(() => files.map(f => ({ f, url: f.type.startsWith('image/') ? URL.createObjectURL(f) : null })), [files]);
  useEffect(() => () => previews.forEach(p => p.url && URL.revokeObjectURL(p.url)), [previews]);

  const add = list => {
    const next = [...files, ...Array.from(list || [])].slice(0, MAX_FILES);
    setFiles(next);
  };
  // Ctrl+V bilan rasmni to'g'ridan-to'g'ri qo'yish
  const onPaste = e => {
    const imgs = [...(e.clipboardData?.files || [])].filter(f => f.type.startsWith('image/'));
    if (imgs.length) { e.preventDefault(); add(imgs); }
  };

  const submit = async () => {
    if (!text.trim() && files.length === 0 && !(editing && existing.length)) return toast.error(t('err.submissionEmpty'));
    if (!honest) return toast.error(t('assign.honestRequired'));
    const fd = new FormData();
    fd.append('text', text.trim());
    files.forEach(f => fd.append('files', f));
    setBusy(true);
    try {
      await api.post(`/assignments/${a.id}/submit`, fd);
      toast.success(editing ? t('assign.updated') : t('assign.submitted'));
      onDone?.();
    } catch (err) { toast.error(errMsg(err)); } finally { setBusy(false); }
  };

  return (
    <Modal open={!!a} onClose={onClose} title={a?.title} size="lg"
      footer={<><button className="btn btn-ghost" onClick={onClose}>{t('common.cancel')}</button>
        <button className="btn btn-primary" onClick={submit} disabled={busy}>{busy ? <Spinner size={16} /> : <Send size={16} />} {editing ? t('assign.resubmit', { n: penalty }) : t('assign.submit')}</button></>}>
      {a && (
        <div className="stack" onPaste={onPaste}>
          {a.description && <p className="text-2" style={{ whiteSpace: 'pre-wrap' }}>{a.description}</p>}
          {a.file_url && <FileChips urls={[a.file_url]} />}
          {editing && <div className="alert alert-warning">⚠️ <span>{t('assign.resubmitWarn', { n: penalty })}</span></div>}

          <div className={`sm-drop ${over ? 'over' : ''}`} onClick={() => input.current?.click()}
            onDragOver={e => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
            onDrop={e => { e.preventDefault(); setOver(false); add(e.dataTransfer.files); }}>
            <UploadCloud size={26} /><strong>{t('assign.dropFiles')}</strong>
            <span className="hint">.py .zip .jpg .jpeg .png .pdf .txt .html .css .js · 25 MB · {t('assign.pasteHint')}</span>
            <input ref={input} type="file" multiple accept={ACCEPT} hidden onChange={e => { add(e.target.files); e.target.value = ''; }} />
          </div>
          {previews.length > 0 && (
            <div className="sm-files">
              {previews.map((p, i) => (
                <div key={i} className="sm-file">
                  {p.url ? <img src={p.url} alt="" /> : <span className="sm-doc"><FileText size={20} /></span>}
                  <span className="sm-name">{p.f.name}</span>
                  <button className="sm-x" onClick={() => setFiles(fs => fs.filter((_, k) => k !== i))} aria-label="remove"><X size={14} /></button>
                </div>
              ))}
            </div>
          )}
          {editing && existing.length > 0 && <div><label className="label">{files.length ? t('assign.willReplace') : t('assign.currentFiles')}</label><FileChips urls={existing} /></div>}

          <div className="field" style={{ marginBottom: 0 }}>
            <label>{t('assign.answerText')}</label>
            <textarea className="textarea" value={text} onChange={e => setText(e.target.value)} />
          </div>
          <label className="sm-honest"><input type="checkbox" checked={honest} onChange={e => setHonest(e.target.checked)} /><span>{t('assign.honest')}</span></label>
        </div>
      )}
    </Modal>
  );
}
