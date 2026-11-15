import { useCallback, useEffect, useState } from 'react';
import api from '../api/axios';

/** Guruhlar ro'yxati + tanlangan guruh (localStorage da eslab qolinadi) */
export default function useGroups() {
  const [groups, setGroups] = useState([]);
  const [loading, setLoading] = useState(true);
  const [groupId, setGroupIdState] = useState(() => Number(localStorage.getItem('aedu_group')) || null);

  const reload = useCallback(async () => {
    try {
      const { data } = await api.get('/groups');
      setGroups(data);
      setGroupIdState(cur => (data.some(g => g.id === cur) ? cur : data[0]?.id ?? null));
      return data;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload().catch(() => {}); }, [reload]);

  const setGroupId = useCallback(id => {
    setGroupIdState(id);
    if (id) localStorage.setItem('aedu_group', String(id));
  }, []);

  return { groups, loading, groupId, setGroupId, group: groups.find(g => g.id === groupId) || null, reload };
}
