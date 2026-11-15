import { useCallback, useEffect, useRef, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { ArrowUp, FileText, ImagePlus, Menu, MessageSquarePlus, Pencil, Sparkles, Square, Trash2, X } from 'lucide-react';
import ChatMessage from '../../components/ChatMessage';
import Translator from '../../components/Translator';
import { SkeletonList } from '../../components/Loader';
import { useLang } from '../../context/LangContext';
import { useToast } from '../../components/Toast';
import api, { API_BASE_URL, errMsg, getLang, getToken } from '../../api/axios';
import './student.css';

export default function UztozAI() {
  const { t } = useLang();
  const toast = useToast();
  const [sessions, setSessions] = useState(null);
  const [activeId, setActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [image, setImage] = useState(null);
  const [attachment, setAttachment] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [side, setSide] = useState(false);
  const [configured, setConfigured] = useState(true);
  const [status, setStatus] = useState(null);
  const [models, setModels] = useState([]);
  const [selectedModel, setSelectedModel] = useState('');
  const [tab, setTab] = useState('chat'); // chat | translate
  const [params] = useSearchParams();
  const [ctx, setCtx] = useState(Number(params.get('a')) || '');
  const [assignments, setAssignments] = useState([]);
  const abort = useRef(null);
  const endRef = useRef(null);
  const taRef = useRef(null);
  const imageInputRef = useRef(null);
  const fileInputRef = useRef(null);
  const imageUrls = useRef(new Set());
  const sessionLoad = useRef(0);

  const clearMediaUrls = () => {
    imageUrls.current.forEach(url => URL.revokeObjectURL(url));
    imageUrls.current.clear();
  };
  useEffect(() => () => {
    clearMediaUrls();
  }, []);
  const loadSessions = useCallback(() => api.get('/ai/sessions').then(r => { setSessions(r.data); return r.data; }).catch(() => setSessions([])), []);
  const loadStatus = useCallback(() => api.get('/ai/status').then(r => { setStatus(r.data); setConfigured(r.data.configured); }).catch(() => {}), []);
  const loadModels = useCallback(() => api.get('/ai/models').then(({ data }) => {
    const choices = data.models || [];
    setModels(choices);
    setSelectedModel(current => choices.some(model => model.id === current) ? current : (data.default_model || ''));
  }).catch(err => {
    setModels([]);
    toast.error(errMsg(err));
  }), [toast]);
  useEffect(() => {
    loadSessions(); loadStatus(); loadModels();
    Promise.all([
      api.get('/assignments/mine', { params: { kind: 'homework', status: 'pending' } }),
      api.get('/assignments/mine', { params: { kind: 'homework', status: 'done' } })
    ]).then(([homework, completedHomework]) =>
      setAssignments([...homework.data, ...completedHomework.data])
    ).catch(() => {});
  }, [loadSessions, loadStatus, loadModels]);
  const exhausted = status && status.remaining === 0;
  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth', block: 'end' }); }, [messages]);
  useEffect(() => { const el = taRef.current; if (el) { el.style.height = 'auto'; el.style.height = `${Math.min(el.scrollHeight, 180)}px`; } }, [input]);

  const openSession = async id => {
    const requestId = ++sessionLoad.current;
    clearMediaUrls();
    setActiveId(id); setSide(false); setMessages([]);
    try {
      const { data } = await api.get(`/ai/sessions/${id}/messages`);
      const hydrated = await Promise.all(data.map(async message => {
        const mediaUrl = message.image_url || message.attachment_url;
        if (!mediaUrl) return message;
        try {
          const response = await api.get(mediaUrl, { responseType: 'blob' });
          const objectUrl = URL.createObjectURL(response.data);
          imageUrls.current.add(objectUrl);
          return message.image_url
            ? { ...message, image: objectUrl }
            : { ...message, attachment: { name: message.attachment_name, kind: message.attachment_kind, url: objectUrl } };
        } catch (err) {
          toast.error(errMsg(err));
          return message;
        }
      }));
      if (requestId === sessionLoad.current) setMessages(hydrated);
      else hydrated.forEach(message => {
        const objectUrl = message.image || message.attachment?.url;
        if (objectUrl && imageUrls.current.has(objectUrl)) {
          URL.revokeObjectURL(objectUrl);
          imageUrls.current.delete(objectUrl);
        }
      });
    } catch (err) { toast.error(errMsg(err)); }
  };
  const newChat = () => {
    sessionLoad.current += 1;
    clearMediaUrls();
    abort.current?.abort(); setActiveId(null); setMessages([]); setSide(false); setInput(''); setImage(null); setAttachment(null);
    taRef.current?.focus();
  };

  const selectImage = event => {
    const file = event.target.files?.[0];
    event.target.value = '';
    if (!file) return;
    if (!['image/jpeg', 'image/png', 'image/webp'].includes(file.type)) {
      toast.error(t('ai.imageType'));
      return;
    }
    if (file.size > 5 * 1024 * 1024) {
      toast.error(t('ai.imageSize'));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => setImage({ name: file.name, dataUrl: String(reader.result) });
    reader.onerror = () => toast.error(t('ai.imageReadError'));
    reader.readAsDataURL(file);
  };

  const readAttachment = file => {
    if (!file) return;
    const extension = file.name.split('.').pop()?.toLowerCase();
    const documentTypes = {
      pdf: 'application/pdf', docx: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
      txt: 'text/plain', md: 'text/markdown', py: 'text/x-python', js: 'text/javascript', jsx: 'text/javascript',
      ts: 'text/typescript', tsx: 'text/typescript', java: 'text/x-java', c: 'text/x-c', cpp: 'text/x-c++',
      cs: 'text/x-csharp', html: 'text/html', css: 'text/css', sql: 'text/x-sql', json: 'application/json',
      go: 'text/x-go', rs: 'text/x-rust', php: 'text/x-php', rb: 'text/x-ruby', zip: 'application/zip'
    };
    const mime = documentTypes[extension];
    if (!mime) {
      toast.error(t('ai.fileType'));
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      toast.error(t('ai.fileSize'));
      return;
    }
    const reader = new FileReader();
    reader.onload = () => {
      const encoded = String(reader.result).split(',')[1];
      if (!encoded) return toast.error(t('ai.fileReadError'));
      setAttachment({ name: file.name, kind: 'document', mime, dataUrl: `data:${mime};base64,${encoded}` });
    };
    reader.onerror = () => toast.error(t('ai.fileReadError'));
    reader.readAsDataURL(file);
  };

  const selectAttachment = event => {
    const file = event.target.files?.[0];
    event.target.value = '';
    readAttachment(file);
  };

  const rename = async s => {
    const title = window.prompt(t('ai.rename'), s.title || '');
    if (!title?.trim()) return;
    try { await api.put(`/ai/sessions/${s.id}`, { title: title.trim() }); loadSessions(); } catch (err) { toast.error(errMsg(err)); }
  };
  const remove = async s => {
    if (!window.confirm(t('ai.deleteConfirm'))) return;
    try { await api.delete(`/ai/sessions/${s.id}`); if (s.id === activeId) newChat(); loadSessions(); } catch (err) { toast.error(errMsg(err)); }
  };

  const send = async text => {
    const attachedImage = image;
    const attachedFile = attachment;
    const content = (text ?? input).trim();
    if ((!content && !attachedImage && !attachedFile) || streaming || exhausted) return;
    setInput('');
    let sid = activeId;
    try {
      if (!sid) { const { data } = await api.post('/ai/sessions'); sid = data.id; setActiveId(sid); }
    } catch (err) { return toast.error(errMsg(err)); }

    const userContent = content || t(attachedImage ? 'ai.imagePrompt' : 'ai.filePrompt');
    const userMessage = {
      id: `u${Date.now()}`, role: 'user', content: userContent, image: attachedImage?.dataUrl,
      attachment: attachedFile ? { name: attachedFile.name, kind: attachedFile.kind, url: attachedFile.dataUrl } : null
    };
    setMessages(m => [...m, userMessage, { id: 'stream', role: 'assistant', content: '' }]);
    setStreaming(true);
    const ac = new AbortController();
    abort.current = ac;
    try {
      const res = await fetch(`${API_BASE_URL}/ai/sessions/${sid}/stream`, {
        method: 'POST', signal: ac.signal,
        headers: { 'Content-Type': 'application/json', Authorization: `Bearer ${getToken()}`, 'X-Lang': getLang() },
        body: JSON.stringify({
          content,
          image_data: attachedImage?.dataUrl || null,
          file_data: attachedFile?.kind === 'document' || attachedFile?.kind === 'code' ? attachedFile.dataUrl : null,
          file_name: attachedFile?.kind === 'document' || attachedFile?.kind === 'code' ? attachedFile.name : null,
          assignment_id: ctx || null,
          model: selectedModel || null
        })
      });
      if (!res.ok) {
        const j = await res.json().catch(() => ({}));
        throw new Error(j.detail || t('ai.error'));
      }
      if (attachedImage) setImage(null);
      if (attachedFile) setAttachment(null);
      const reader = res.body.getReader();
      const dec = new TextDecoder();
      let buf = '';
      for (;;) {
        const { value, done } = await reader.read();
        if (done) break;
        buf += dec.decode(value, { stream: true });
        const parts = buf.split('\n\n');
        buf = parts.pop();
        for (const p of parts) {
          if (!p.startsWith('data:')) continue;
          const ev = JSON.parse(p.slice(5));
          if (ev.delta) setMessages(m => m.map(x => (x.id === 'stream' ? { ...x, content: x.content + ev.delta } : x)));
          if (ev.error) throw new Error(ev.error);
        }
      }
    } catch (err) {
      if (err.name !== 'AbortError') {
        toast.error(err.message);
        setMessages(m => m.filter(x => !(x.id === 'stream' && !x.content)));
      }
    } finally {
      setMessages(m => m.map(x => (x.id === 'stream' ? { ...x, id: `a${Date.now()}` } : x)));
      setStreaming(false);
      loadSessions();
      loadStatus();
    }
  };

  const onKey = e => { if (e.key === 'Enter' && !e.shiftKey && !e.nativeEvent.isComposing) { e.preventDefault(); send(); } };
  const sugs = [t('ai.sug1'), t('ai.sug2'), t('ai.sug3'), t('ai.sug4')];

  return (
    <div className="ai">
      <aside className={`ai-side ${side ? 'open' : ''}`}>
        <button className="btn btn-primary btn-block" onClick={newChat}><MessageSquarePlus size={18} /> {t('ai.newChat')}</button>
        <div className="label" style={{ padding: '4px 6px' }}>{t('ai.history')}</div>
        <div className="ai-sessions">
          {sessions === null ? <SkeletonList n={4} h={40} /> : sessions.length === 0 ? <p className="hint" style={{ padding: 8 }}>{t('ai.noChats')}</p> : sessions.map(s => (
            <div key={s.id} className={`ai-s ${s.id === activeId ? 'active' : ''}`} onClick={() => openSession(s.id)}>
              <span className="t">{s.title || t('ai.untitled')}</span>
              <span className="acts"><button onClick={e => { e.stopPropagation(); rename(s); }} aria-label="rename"><Pencil size={14} /></button><button onClick={e => { e.stopPropagation(); remove(s); }} aria-label="delete"><Trash2 size={14} /></button></span>
            </div>
          ))}
        </div>
      </aside>
      <section className="ai-main">
        <div className="ai-tabs">
          <div className="tabs">
            <button className={`tab ${tab === 'chat' ? 'active' : ''}`} onClick={() => setTab('chat')}>💬 {t('ai.tabChat')}</button>
            <button className={`tab ${tab === 'translate' ? 'active' : ''}`} onClick={() => setTab('translate')}>🌐 {t('ai.tabTranslate')}</button>
          </div>
          <label className="row" style={{ gap: 8 }}>
            <span className="hint">{t('ai.model')}</span>
            <select className="select" value={selectedModel} onChange={e => setSelectedModel(e.target.value)} disabled={streaming || models.length === 0} aria-label={t('ai.chooseModel')}>
              {models.length === 0 && <option value="">—</option>}
              {models.map(model => <option key={model.id} value={model.id}>{model.name}</option>)}
            </select>
          </label>
        </div>
        {tab === 'translate' ? <Translator model={selectedModel} /> : <>
        <div className="ai-head"><button className="btn btn-ghost btn-icon btn-sm" onClick={() => setSide(s => !s)}><Menu size={18} /></button><strong>Ustoz AI</strong></div>
        <div className="ai-msgs">
          {!configured && <div className="alert alert-warning" style={{ maxWidth: 860, margin: '0 auto 18px' }}>{t('ai.notConfigured')}</div>}
          {messages.length === 0 ? (
            <div className="ai-welcome anim-fade-up">
              <div className="big"><Sparkles size={38} /></div>
              <h1>Ustoz AI</h1><p className="text-2" style={{ marginTop: 8 }}>{t('ai.welcome')}</p>
              <div className="ai-sugs">{sugs.map(s => <button key={s} className="ai-sug" onClick={() => send(s)}>{s}</button>)}</div>
            </div>
          ) : messages.map(m => <ChatMessage key={m.id} role={m.role} content={m.content} image={m.image} attachment={m.attachment} streaming={streaming && m.id === 'stream'} />)}
          <div ref={endRef} />
        </div>
        <div className="ai-compose">
          <div className="ai-ctx">
            <select className="select" value={ctx} onChange={e => setCtx(Number(e.target.value) || '')} disabled={exhausted}>
              <option value="">💬 {t('ai.general')}</option>
              {assignments.map(a => <option key={a.id} value={a.id}>{a.submission?.submitted_at ? '✅' : a.kind === 'task' ? '⏱' : '📝'} {a.title}</option>)}
            </select>
            {status && <span className={`badge ${exhausted ? 'badge-danger' : status.remaining <= 3 ? 'badge-warning' : 'badge-primary'}`}>{t('ai.left', { n: status.remaining, m: status.limit })}</span>}
          </div>
          {(image || attachment) && (
            <div className="ai-image-preview">
              {image ? <img src={image.dataUrl} alt={image.name} /> : <FileText size={22} />}
              <span>{(image || attachment).name}</span>
              <button type="button" className="btn btn-ghost btn-icon btn-sm" onClick={() => { setImage(null); setAttachment(null); }} aria-label={t('ai.removeAttachment')}>
                <X size={16} />
              </button>
            </div>
          )}
          <div className={`ai-box ${exhausted ? 'locked' : ''}`}>
            <textarea ref={taRef} rows={1} value={input} onChange={e => setInput(e.target.value)} onKeyDown={onKey} disabled={exhausted}
              placeholder={exhausted ? t('ai.limitReached') : t('ai.placeholder')} maxLength={8000} />
            <input ref={imageInputRef} className="ai-file-input" type="file" accept="image/jpeg,image/png,image/webp" onChange={selectImage} disabled={streaming || exhausted} />
            <button type="button" className="btn btn-icon btn-ghost" onClick={() => imageInputRef.current?.click()} disabled={streaming || exhausted || !!attachment} aria-label={t('ai.attachImage')}>
              <ImagePlus size={19} />
            </button>
            <input ref={fileInputRef} className="ai-file-input" type="file" accept=".pdf,.docx,.txt,.md,.py,.js,.jsx,.ts,.tsx,.java,.c,.cpp,.cs,.html,.css,.sql,.json,.go,.rs,.php,.rb,.zip" onChange={selectAttachment} disabled={streaming || exhausted} />
            <button type="button" className="btn btn-icon btn-ghost" onClick={() => fileInputRef.current?.click()} disabled={streaming || exhausted || !!image} aria-label={t('ai.attachFile')}>
              <FileText size={19} />
            </button>
            {streaming
              ? <button className="btn btn-icon btn-danger" onClick={() => abort.current?.abort()} aria-label="stop"><Square size={16} fill="currentColor" /></button>
              : <button className="btn btn-icon btn-primary" disabled={(!input.trim() && !image && !attachment) || exhausted} onClick={() => send()} aria-label="send"><ArrowUp size={20} /></button>}
          </div>
          <p className="ai-note">{t('ai.note')}</p>
        </div>
        </>}
      </section>
    </div>
  );
}
