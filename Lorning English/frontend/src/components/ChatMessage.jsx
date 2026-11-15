import { useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Check, Copy, FileText, Sparkles, UserRound } from 'lucide-react';
import './ChatMessage.css';

function CodeBlock({ children, className }) {
  const [copied, setCopied] = useState(false);
  const lang = /language-(\w+)/.exec(className || '')?.[1] || 'code';
  const text = String(children).replace(/\n$/, '');
  const copy = () => {
    navigator.clipboard?.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1500);
  };
  return (
    <div className="code-block">
      <div className="code-head"><span>{lang}</span><button onClick={copy}>{copied ? <Check size={14} /> : <Copy size={14} />}</button></div>
      <pre><code>{text}</code></pre>
    </div>
  );
}

export default function ChatMessage({ role, content, image, attachment, streaming }) {
  const isUser = role === 'user';
  return (
    <div className={`chat-msg ${isUser ? 'user' : 'bot'}`}>
      <div className="chat-ava">{isUser ? <UserRound size={18} /> : <Sparkles size={18} />}</div>
      <div className="chat-bubble">
        {image && <img className="chat-image" src={image} alt="Attached to this message" />}
        {attachment?.url && (
          <a className="chat-attachment" href={attachment.url} download={attachment.name}><FileText size={17} />{attachment.name}</a>
        )}
        {isUser ? (
          <p className="chat-plain">{content}</p>
        ) : (
          <div className="markdown">
            <ReactMarkdown
              remarkPlugins={[remarkGfm]}
              components={{
                pre: ({ children }) => <>{children}</>,
                code: ({ inline, className, children }) =>
                  inline || !/\n/.test(String(children)) && !className
                    ? <code className="inline-code">{children}</code>
                    : <CodeBlock className={className}>{children}</CodeBlock>
              }}
            >
              {content || ''}
            </ReactMarkdown>
            {streaming && <span className="caret" />}
          </div>
        )}
      </div>
    </div>
  );
}
