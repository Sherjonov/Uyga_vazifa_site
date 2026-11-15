import { useEffect, useState } from 'react';
import { BookOpen, Eye } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import BookViewer from '../../components/BookViewer';
import { Empty, SkeletonList } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import api from '../../api/axios';
import '../../styles/extra.css';

/** O'quvchi: Dars kitobi va Lug'at kitobi (PDF ko'rish: qidiruv, sahifaga o'tish, full screen) */
export default function Books() {
  const { t } = useLang();
  const [type, setType] = useState('lesson');
  const [books, setBooks] = useState(null);
  const [view, setView] = useState(null);
  useEffect(() => { setBooks(null); api.get('/books', { params: { type } }).then(r => setBooks(r.data)).catch(() => setBooks([])); }, [type]);

  return (
    <div className="page page-wide">
      <PageHeader icon={BookOpen} title={t('nav.books')} subtitle={t('book.studentSub')} />
      {view ? (
        <div className="stack"><button className="btn btn-ghost" style={{ alignSelf: 'flex-start' }} onClick={() => setView(null)}>← {t('common.back')}</button><BookViewer url={view.pdf_url} title={view.title} /></div>
      ) : (
        <div className="stack" style={{ gap: 18 }}>
          <div className="tabs" style={{ alignSelf: 'flex-start' }}>
            <button className={`tab ${type === 'lesson' ? 'active' : ''}`} onClick={() => setType('lesson')}>{t('book.lesson')}</button>
            <button className={`tab ${type === 'vocab' ? 'active' : ''}`} onClick={() => setType('vocab')}>{t('book.vocab')}</button>
          </div>
          {books === null ? <SkeletonList n={2} h={80} /> : books.length === 0 ? <div className="card"><Empty icon={BookOpen} title={t('book.none')} /></div> : (
            <div className="grid grid-2 stagger">
              {books.map(b => (
                <div key={b.id} className="card row-between">
                  <div><strong>{b.title}</strong><div className="hint">{b.group_name} · {b.page_count} {t('book.pages')}</div></div>
                  <button className="btn btn-primary btn-sm" onClick={() => setView(b)}><Eye size={15} /> {t('book.open')}</button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
