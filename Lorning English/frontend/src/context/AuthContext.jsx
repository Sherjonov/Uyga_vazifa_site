import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import api, { getLang, getToken } from '../api/axios';

const AuthContext = createContext(null);
export const useAuth = () => useContext(AuthContext);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(!!getToken());

  // Foydalanuvchi ko'rib turgan til va mavzu server bilan sinxronlanadi (UI tanlovi ustun)
  const syncPrefs = useCallback(() => {
    api.put('/settings/preferences', { language: getLang(), theme: localStorage.getItem('aedu_theme') || 'dark' }).catch(() => {});
  }, []);

  useEffect(() => {
    if (!getToken()) return;
    api
      .get('/auth/me')
      .then(r => setUser(r.data))
      .catch(() => localStorage.removeItem('aedu_token'))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  /** Login/ro'yxatdan o'tishdan keyin tokenni saqlaydi */
  const startSession = useCallback(
    (token, u, sync = true) => {
      localStorage.setItem('aedu_token', token);
      setUser(u);
      if (sync) syncPrefs();
    },
    [syncPrefs]
  );

  const login = useCallback(
    async (identifier, password) => {
      const { data } = await api.post('/auth/login', { identifier, password });
      startSession(data.access_token, data.user);
      return data.user;
    },
    [startSession]
  );

  const logout = useCallback(() => {
    localStorage.removeItem('aedu_token');
    setUser(null);
  }, []);

  const refresh = useCallback(async () => {
    const { data } = await api.get('/auth/me');
    setUser(data);
    return data;
  }, []);

  return (
    <AuthContext.Provider value={{ user, setUser, loading, login, logout, refresh, startSession }}>
      {children}
    </AuthContext.Provider>
  );
}
