import { createContext, useCallback, useContext, useMemo, useState } from 'react';
import { CheckCircle2, Info, TriangleAlert, X } from 'lucide-react';
import './Toast.css';

const ToastContext = createContext(null);
export const useToast = () => useContext(ToastContext);

const ICONS = { success: CheckCircle2, error: TriangleAlert, info: Info };

export function ToastProvider({ children }) {
  const [items, setItems] = useState([]);

  const remove = useCallback(id => setItems(list => list.filter(i => i.id !== id)), []);
  const push = useCallback(
    (type, message) => {
      const id = Date.now() + Math.random();
      setItems(list => [...list.slice(-3), { id, type, message }]);
      setTimeout(() => remove(id), type === 'error' ? 6000 : 4000);
    },
    [remove]
  );
  const api = useMemo(
    () => ({
      success: m => push('success', m),
      error: m => push('error', m),
      info: m => push('info', m)
    }),
    [push]
  );

  return (
    <ToastContext.Provider value={api}>
      {children}
      <div className="toast-stack" role="status" aria-live="polite">
        {items.map(i => {
          const Icon = ICONS[i.type];
          return (
            <div key={i.id} className={`toast toast-${i.type}`}>
              <Icon size={20} />
              <span>{i.message}</span>
              <button className="toast-x" onClick={() => remove(i.id)} aria-label="close"><X size={16} /></button>
            </div>
          );
        })}
      </div>
    </ToastContext.Provider>
  );
}
