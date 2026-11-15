import { useRef, useState } from 'react';
import { FileText, UploadCloud, X } from 'lucide-react';
import { useLang } from '../context/LangContext';
import './FileDrop.css';

const size = bytes => (bytes > 1048576 ? `${(bytes / 1048576).toFixed(1)} MB` : `${Math.max(1, Math.round(bytes / 1024))} KB`);

/** Yagona PDF/fayl yuklash maydoni: tashlash (drag & drop), tanlash, fayl nomi va hajmi, olib tashlash. */
export default function FileDrop({ file, onChange, accept = 'application/pdf,.pdf', label, hint, disabled }) {
  const { t } = useLang();
  const input = useRef(null);
  const [over, setOver] = useState(false);
  const pick = f => { if (f && !disabled) onChange(f); };
  return (
    <div className={`filedrop ${over ? 'over' : ''} ${file ? 'has-file' : ''} ${disabled ? 'disabled' : ''}`} role="button" tabIndex={0}
      onClick={() => !disabled && input.current?.click()}
      onKeyDown={e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); input.current?.click(); } }}
      onDragOver={e => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
      onDrop={e => { e.preventDefault(); setOver(false); pick(e.dataTransfer.files[0]); }}>
      <span className="filedrop-ico">{file ? <FileText size={26} /> : <UploadCloud size={26} />}</span>
      <span className="filedrop-body">
        <strong>{file ? file.name : (label || t('lessons.dropPdf'))}</strong>
        <span className="hint">{file ? size(file.size) : (hint || 'PDF')}</span>
      </span>
      {file && <button type="button" className="btn btn-ghost btn-icon btn-sm" aria-label="Remove" onClick={e => { e.stopPropagation(); onChange(null); if (input.current) input.current.value = ''; }}><X size={16} /></button>}
      <input ref={input} type="file" accept={accept} hidden onChange={e => { pick(e.target.files[0]); e.target.value = ''; }} />
    </div>
  );
}
