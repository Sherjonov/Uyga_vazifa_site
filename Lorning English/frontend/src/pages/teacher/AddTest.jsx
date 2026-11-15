import { useCallback, useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { BarChart3, Eye, EyeOff, FilePlus2, Pencil, Plus, Save, Sparkles, Trash2, UploadCloud, Users, X } from 'lucide-react';
import PageHeader from '../../components/PageHeader';
import GroupSelect from '../../components/GroupSelect';
import Modal from '../../components/Modal';
import RetakeRequests from './RetakeRequests';
import DataTable from '../../components/DataTable';
import { Empty, SkeletonList, Spinner } from '../../components/Loader';
import useGroups from '../../utils/useGroups';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { errMsg } from '../../api/axios';
import { num } from '../../utils/format';
import './teacher.css';

const blankQ = () => ({ text: '', options: ['', '', '', ''], correct_index: null });

export default function AddTest() {
  const { t } = useLang();
  const toast = useToast();
  const { groups, groupId, setGroupId, loading: gl } = useGroups();
  const [items, setItems] = useState(null);
  const [ed, setEd] = useState(null); // muharrir: {id?, title, minutes, questions, method}
  const [parsing, setParsing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [results, setResults] = useState(null);
  const [over, setOver] = useState(false);
  const [retakeKey, setRetakeKey] = useState(0);
  const [gen, setGen] = useState({ topic: '', count: 20, options: 4 });
  const [models, setModels] = useState([]);
  const [model, setModel] = useState('');
  const [generating, setGenerating] = useState(false);
  const [replacing, setReplacing] = useState(null);
  const input = useRef(null);

  useEffect(() => {
    let active = true;
    api.get('/ai/models').then(({ data }) => {
      if (!active) return;
      const available = Array.isArray(data.models) ? data.models : [];
      setModels(available);
      setModel(current => available.some(item => item.id === current)
        ? current
        : (data.default_model || available[0]?.id || ''));
    }).catch(err => {
      if (active) toast.error(errMsg(err));
    });
    return () => { active = false; };
  }, [toast]);

  const load = useCallback(() => {
    if (!groupId) return setItems([]);
    api.get('/tests', { params: { group_id: groupId } }).then(r => setItems(r.data)).catch(() => setItems([]));
  }, [groupId]);
  useEffect(() => { if (!gl) { setItems(null); load(); } }, [gl, load]);

  const parsePdf = async file => {
    if (!file) return;
    const fd = new FormData(); fd.append('file', file);
    setParsing(true);
    try {
      const { data } = await api.post('/tests/parse', fd);
      setEd({ title: file.name.replace(/\.pdf$/i, ''), minutes: 30, questions: data.questions, method: data.method });
      toast.success(t('test.parsed', { n: data.questions.length }));
    } catch (err) { toast.error(errMsg(err)); } finally { setParsing(false); }
  };

  const generate = async () => {
    const count = Number(gen.count); const options = Number(gen.options);
    if (gen.topic.trim().length < 2 || !(count >= 1 && count <= 50) || !(options >= 2 && options <= 6)) return toast.error(t('test.genInvalid'));
    setGenerating(true);
    try {
      const { data } = await api.post('/tests/generate', { topic: gen.topic.trim(), count, options_count: options, model: model || null }, { timeout: 180000 });
      setEd({ title: gen.topic.trim(), minutes: 30, questions: data.questions.map(q => ({ text: q.text, options: q.options, correct_index: q.correct_index, explanation: q.explanation })), method: 'ai', topic: gen.topic.trim() });
      toast.success(t('test.parsed', { n: data.questions.length }));
    } catch (err) { toast.error(errMsg(err)); } finally { setGenerating(false); }
  };
  const replaceQ = async i => {
    setReplacing(i);
    try {
      const { data } = await api.post('/tests/generate/replace', { topic: ed.topic || ed.title, options_count: ed.questions[i].options.length, avoid: ed.questions.map(q => q.text), model: model || null }, { timeout: 120000 });
      setQ(i, { text: data.question.text, options: data.question.options, correct_index: data.question.correct_index, explanation: data.question.explanation });
    } catch (err) { toast.error(errMsg(err)); } finally { setReplacing(null); }
  };

  const openEdit = async x => {
    try { const { data } = await api.get(`/tests/${x.id}`); setEd({ id: x.id, title: data.title, minutes: data.duration_minutes, questions: data.questions.map(q => ({ text: q.text, options: q.options, correct_index: q.correct_index, explanation: q.explanation })), published: data.is_published, topic: data.title }); } catch (err) { toast.error(errMsg(err)); }
  };

  const setQ = (i, patch) => setEd(e => ({ ...e, questions: e.questions.map((q, k) => (k === i ? { ...q, ...patch } : q)) }));
  const setOpt = (i, j, v) => setQ(i, { options: ed.questions[i].options.map((o, k) => (k === j ? v : o)) });

  const validate = () => {
    if (!ed.title.trim() || !(Number(ed.minutes) >= 1)) return t('err.fillAll');
    for (const q of ed.questions) {
      const opts = q.options.map(o => o.trim());
      if (!q.text.trim() || opts.filter(Boolean).length < 2) return t('test.errQuestion');
      if (q.correct_index == null || !opts[q.correct_index]) return t('test.errCorrect');
    }
    return '';
  };

  const save = async publish => {
    const err = validate();
    if (err) return toast.error(err);
    // bo'sh variantlarni olib tashlab, to'g'ri javob indeksini moslaymiz
    const questions = ed.questions.map(q => {
      const keep = q.options.map((o, i) => ({ o: o.trim(), i })).filter(x => x.o);
      return { text: q.text.trim(), options: keep.map(x => x.o), correct_index: keep.findIndex(x => x.i === q.correct_index), explanation: q.explanation || null };
    });
    setSaving(true);
    try {
      if (ed.id) await api.put(`/tests/${ed.id}`, { title: ed.title.trim(), duration_minutes: Number(ed.minutes), questions, is_published: publish ?? ed.published });
      else await api.post('/tests', { group_id: groupId, title: ed.title.trim(), duration_minutes: Number(ed.minutes), questions, is_published: !!publish });
      toast.success(publish ? t('test.published') : t('common.saved'));
      setEd(null); load();
    } catch (e) { toast.error(errMsg(e)); } finally { setSaving(false); }
  };

  const togglePublish = async x => { try { await api.put(`/tests/${x.id}`, { is_published: !x.is_published }); load(); } catch (err) { toast.error(errMsg(err)); } };
  const remove = async x => { if (!window.confirm(t('common.confirmDelete'))) return; try { await api.delete(`/tests/${x.id}`); load(); } catch (err) { toast.error(errMsg(err)); } };
  const showResults = async x => { try { const { data } = await api.get(`/tests/${x.id}/results`); setResults(data); } catch (err) { toast.error(errMsg(err)); } };

  if (!gl && groups.length === 0) return <div className="page"><div className="card"><Empty icon={Users} title={t('groups.none')} text={t('groups.noneText')} action={<Link to="/teacher/students" className="btn btn-primary">{t('groups.create')}</Link>} /></div></div>;

  return (
    <div className="page">
      <PageHeader icon={FilePlus2} title={t('nav.addTest')} subtitle={t('test.addSub')} />

      {!ed ? (
        <div className="stack" style={{ gap: 28 }}>
          <div className="grid grid-2" style={{ alignItems: 'stretch' }}>
            <div className="card stack">
              <div className="field" style={{ marginBottom: 0 }}><label>{t('groups.group')}</label><GroupSelect groups={groups} value={groupId} onChange={setGroupId} /></div>
              <div className={`drop ${over ? 'over' : ''}`} onClick={() => !parsing && input.current?.click()} onDragOver={e => { e.preventDefault(); setOver(true); }} onDragLeave={() => setOver(false)}
                onDrop={e => { e.preventDefault(); setOver(false); parsePdf(e.dataTransfer.files[0]); }}>
                {parsing ? <><Spinner size={34} /><strong>{t('test.parsing')}</strong></> : <><UploadCloud size={34} /><strong>{t('test.dropPdf')}</strong><span className="hint">{t('test.pdfHint')}</span></>}
                <input ref={input} type="file" accept="application/pdf,.pdf" hidden onChange={e => { parsePdf(e.target.files[0]); e.target.value = ''; }} />
              </div>
              <div className="card stack" style={{ gap: 10, background: 'var(--surface-2)' }}>
                <strong><Sparkles size={16} /> {t('test.aiTitle')}</strong>
                <input className="input" value={gen.topic} maxLength={200} placeholder={t('test.aiTopic')} onChange={e => setGen({ ...gen, topic: e.target.value })} />
                {models.length > 0 && (
                  <div className="field" style={{ marginBottom: 0 }}>
                    <label>{t('ai.model')}</label>
                    <select className="input" value={model} onChange={e => setModel(e.target.value)}>
                      {models.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
                    </select>
                  </div>
                )}
                <div className="grid grid-2" style={{ gap: 10 }}>
                  <div className="field" style={{ marginBottom: 0 }}><label>{t('test.aiCount')}</label><input className="input" type="number" min={1} max={50} value={gen.count} onChange={e => setGen({ ...gen, count: e.target.value })} /></div>
                  <div className="field" style={{ marginBottom: 0 }}><label>{t('test.aiOptions')}</label><input className="input" type="number" min={2} max={6} value={gen.options} onChange={e => setGen({ ...gen, options: e.target.value })} /></div>
                </div>
                <button className="btn btn-primary" disabled={generating} onClick={generate}>{generating ? <Spinner size={16} /> : <Sparkles size={16} />} {generating ? t('test.aiGenerating') : t('test.aiGenerate')}</button>
              </div>
              <button className="btn btn-ghost" onClick={() => setEd({ title: '', minutes: 30, questions: [blankQ()] })}><Plus size={16} /> {t('test.manual')}</button>
            </div>
            <div className="card stack">
              <h3>{t('test.howTitle')}</h3>
              <p className="text-2">{t('test.how1')}</p><p className="text-2">{t('test.how2')}</p><p className="text-2">{t('test.how3')}</p>
            </div>
          </div>

          <div className="stack">
            <h3>{t('test.existing')}</h3>
            {items === null ? <SkeletonList n={2} h={90} /> : items.length === 0 ? <div className="card"><Empty icon={FilePlus2} title={t('test.none')} /></div> : items.map(x => (
              <div key={x.id} className="card row-between">
                <div><strong>{x.title}</strong>
                  <div className="row" style={{ gap: 6, marginTop: 6 }}>
                    <span className="badge">{x.questions_count} {t('tests.questions')}</span><span className="badge">{x.duration_minutes} {t('time.m')}</span>
                    <span className={`badge ${x.is_published ? 'badge-success' : 'badge-warning'}`}>{x.is_published ? t('test.statusPublished') : t('test.statusDraft')}</span>
                    <span className="badge badge-info">{x.finished_count} {t('test.finishedShort')}</span>
                    {x.pending_retakes > 0 && <span className="badge badge-danger">{x.pending_retakes} {t('retake.requestsShort')}</span>}
                  </div></div>
                <div className="row">
                  <button className="btn btn-ghost btn-sm" onClick={() => showResults(x)}><BarChart3 size={15} /> {t('test.results')}</button>
                  <button className="btn btn-ghost btn-sm" onClick={() => togglePublish(x)}>{x.is_published ? <EyeOff size={15} /> : <Eye size={15} />} {x.is_published ? t('test.unpublish') : t('test.publish')}</button>
                  <button className="btn btn-ghost btn-icon btn-sm" onClick={() => openEdit(x)}><Pencil size={15} /></button>
                  <button className="btn btn-danger btn-icon btn-sm" onClick={() => remove(x)}><Trash2 size={15} /></button>
                </div>
              </div>
            ))}
          </div>

          <div className="stack">
            <h3>{t('retake.beside')}</h3>
            <RetakeRequests key={retakeKey} embedded />
          </div>
        </div>
      ) : (
        <div className="stack">
          {ed.method && <div className="alert alert-info"><Sparkles size={18} /> {ed.method === 'ai' ? t('test.parsedAi') : t('test.parsedPlain')} {t('test.reviewHint')}</div>}
          <div className="card grid grid-2" style={{ gap: 14 }}>
            <div className="field" style={{ marginBottom: 0 }}><label>{t('test.title')}</label><input className="input" value={ed.title} onChange={e => setEd({ ...ed, title: e.target.value })} maxLength={200} /></div>
            <div className="field" style={{ marginBottom: 0 }}><label>{t('test.duration')}</label><input className="input" type="number" min={1} max={300} value={ed.minutes} onChange={e => setEd({ ...ed, minutes: e.target.value })} /></div>
          </div>
          {ed.questions.map((q, i) => (
            <div key={i} className="q-edit anim-scale-in">
              <div className="row-between" style={{ marginBottom: 8 }}><strong>{t('test.question')} {i + 1}</strong>
                <div className="row">{ed.method === 'ai' && <button className="btn btn-ghost btn-sm" disabled={replacing === i} onClick={() => replaceQ(i)}>{replacing === i ? <Spinner size={14} /> : <Sparkles size={14} />} {t('test.aiReplace')}</button>}
                <button className="btn btn-danger btn-icon btn-sm" disabled={ed.questions.length === 1} onClick={() => setEd({ ...ed, questions: ed.questions.filter((_, k) => k !== i) })}><Trash2 size={14} /></button></div></div>
              <textarea className="textarea" style={{ minHeight: 70 }} value={q.text} onChange={e => setQ(i, { text: e.target.value })} />
              {q.options.map((o, j) => (
                <div key={j} className="opt-row">
                  <input type="radio" name={`c${i}`} checked={q.correct_index === j} onChange={() => setQ(i, { correct_index: j })} title={t('test.correctAnswer')} />
                  <span className="opt-letter" style={{ width: 28, height: 28, display: 'grid', placeItems: 'center', background: 'var(--surface)', borderRadius: 8, fontWeight: 800, fontSize: '0.8rem' }}>{String.fromCharCode(65 + j)}</span>
                  <input className="input input-sm" value={o} onChange={e => setOpt(i, j, e.target.value)} />
                  <button className="btn btn-ghost btn-icon btn-sm" disabled={q.options.length <= 2} onClick={() => setQ(i, { options: q.options.filter((_, k) => k !== j), correct_index: q.correct_index === j ? null : q.correct_index > j ? q.correct_index - 1 : q.correct_index })}><X size={14} /></button>
                </div>
              ))}
              <div className="row-between" style={{ marginTop: 10 }}>
                <button className="link-btn" disabled={q.options.length >= 6} onClick={() => setQ(i, { options: [...q.options, ''] })}>+ {t('test.addOption')}</button>
                {q.correct_index == null && <span className="badge badge-warning">{t('test.pickCorrect')}</span>}
              </div>
            </div>
          ))}
          <button className="btn btn-ghost" style={{ alignSelf: 'flex-start' }} onClick={() => setEd({ ...ed, questions: [...ed.questions, blankQ()] })}><Plus size={16} /> {t('test.addQuestion')}</button>
          <div className="row" style={{ position: 'sticky', bottom: 14, padding: 14, background: 'var(--glass)', backdropFilter: 'blur(14px)', border: '1px solid var(--border)', borderRadius: 18, boxShadow: 'var(--shadow)' }}>
            <button className="btn btn-ghost" onClick={() => setEd(null)}>{t('common.cancel')}</button><span className="spacer" />
            <button className="btn btn-ghost" disabled={saving} onClick={() => save(false)}>{saving ? <Spinner size={16} /> : <Save size={16} />} {t('test.saveDraft')}</button>
            <button className="btn btn-primary" disabled={saving} onClick={() => save(true)}><Eye size={16} /> {t('test.saveAndPublish')}</button>
          </div>
        </div>
      )}

      <Modal open={!!results} onClose={() => setResults(null)} title={results ? `${results.test.title} — ${t('test.results')}` : ''} size="lg">
        {results && <DataTable rows={results.items.map(r => ({ ...r, id: r.student.id }))} columns={[
          { key: 's', title: t('students.student'), render: r => <strong>{r.student.name}</strong> },
          { key: 'score', title: t('students.score'), render: r => r.score != null ? <span className="score-pill">{num(r.score, 2)}</span> : '–' },
          { key: 'p', title: '%', render: r => (r.percent != null ? `${num(r.percent, 0)}%` : '–') },
          { key: 'a', title: t('test.attempts'), render: r => r.attempts },
          { key: 'st', title: t('parents.status'), render: r => <span className={`badge ${r.status === 'finished' ? 'badge-success' : r.status === 'not_started' ? '' : 'badge-warning'}`}>{t(`test.st.${r.status}`)}</span> }
        ]} />}
      </Modal>
    </div>
  );
}
