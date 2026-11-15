import { Paperclip } from 'lucide-react';
import { fileName, isImage } from '../utils/files';
import './FileChips.css';

/** Yuklangan fayllar: rasm bo'lsa kichik ko'rinishda, boshqalari nom bilan */
export default function FileChips({ urls = [] }) {
  if (!urls.length) return null;
  return (
    <div className="file-chips">
      {urls.map(u => isImage(u)
        ? <a key={u} className="file-thumb" href={u} target="_blank" rel="noreferrer"><img src={u} alt={fileName(u)} loading="lazy" /></a>
        : <a key={u} className="badge badge-info" href={u} target="_blank" rel="noreferrer"><Paperclip size={12} /> {fileName(u)}</a>)}
    </div>
  );
}
