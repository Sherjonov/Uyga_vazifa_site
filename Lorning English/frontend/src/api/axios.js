import axios from 'axios';

const NET = {
  uz: "Serverga ulanib bo'lmadi. Internetni tekshiring",
  en: 'Could not reach the server. Check your connection',
  ru: 'Не удалось подключиться к серверу. Проверьте интернет'
};

export const getLang = () => localStorage.getItem('aedu_lang') || 'uz';
export const getToken = () => localStorage.getItem('aedu_token');

const DEFAULT_API_URL = import.meta.env.PROD
  ? 'https://aedu-production-bfdd9ae0.up.railway.app/api'
  : '/api';
export const API_BASE_URL = (import.meta.env.VITE_API_URL || DEFAULT_API_URL).replace(/\/+$/, '');
const api = axios.create({ baseURL: API_BASE_URL, timeout: 60000 });

api.interceptors.request.use(cfg => {
  const token = getToken();
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  cfg.headers['X-Lang'] = getLang();
  return cfg;
});

api.interceptors.response.use(
  r => r,
  err => {
    const url = err.config?.url || '';
    if (err.response?.status === 401 && !url.includes('/auth/login')) {
      localStorage.removeItem('aedu_token');
      if (!window.location.pathname.startsWith('/login')) window.location.href = '/login';
    }
    if (err.response?.status === 402 && !window.location.pathname.startsWith('/teacher/subscription')) {
      window.location.href = '/teacher/subscription';
    }
    return Promise.reject(err);
  }
);

/** Foydalanuvchiga ko'rinadigan xato matni (backend allaqachon 3 tilda qaytaradi) */
export const errMsg = err => {
  const d = err?.response?.data?.detail;
  if (typeof d === 'string') return d;
  if (!err?.response) return NET[getLang()] || NET.uz;
  return NET[getLang()] || 'Error';
};

export default api;
