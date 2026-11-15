import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams } from 'react-router-dom';
import { ArrowLeft, Download, Presentation } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import SlideDeck from '../../components/SlideDeck';
import { Empty, SkeletonList } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { fmtDate } from '../../utils/format';
import './student.css';

function LessonView({ id }) {
  const { t } = useLang();
  const toast = useToast();
  const nav = useNavigate();
  const [lesson, setLesson] = useState(null);
  useEffect(() => {
    api.get(`/lessons/${id}`).then(r => setLesson(r.data)).catch(err => { toast.error(errMsg(err)); nav('/student/lessons'); });
  }, [id]); // eslint-disable-line react-hooks/exhaustive-deps

  return (
    <div className="page page-wide">
      <PageHeader title={lesson?.title || '…'} subtitle={lesson ? `${lesson.page_count} ${t('lessons.slides')}` : ''}
        actions={<>
          <Link to="/student/lessons" className="btn btn-ghost"><ArrowLeft size={16} /> {t('common.back')}</Link>
          {lesson && <a className="btn btn-ghost" href={lesson.pdf_url} target="_blank" rel="noreferrer"><Download size={16} /> PDF</a>}
        </>} />
      {!lesson ? <SkeletonList n={1} h={420} /> : <SlideDeck slides={lesson.slides} title={lesson.title} />}
    </div>
  );
}

export default function Lessons() {
  const { id } = useParams();
  const { t, lang } = useLang();
  const [items, setItems] = useState(null);
  useEffect(() => { if (!id) api.get('/lessons').then(r => setItems(r.data)).catch(() => setItems([])); }, [id]);

  if (id) return <LessonView id={id} />;
  return (
    <div className="page">
      <PageHeader icon={Presentation} title={t('nav.lessons')} subtitle={t('lessons.subtitle')} />
      {items === null ? <SkeletonList n={3} /> : items.length === 0 ? <div className="card"><Empty icon={Presentation} title={t('lessons.empty')} text={t('lessons.emptyText')} /></div> : (
        <div className="grid grid-auto stagger">
          {items.map(l => (
            <Link key={l.id} to={`/student/lessons/${l.id}`} className="card card-hover lesson-card">
              <div className="lesson-ico"><Presentation size={26} /></div>
              <div><strong>{l.title}</strong><div className="hint">{l.page_count} {t('lessons.slides')} · {fmtDate(l.created_at, lang)}</div></div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
