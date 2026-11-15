import { useEffect, useState } from 'react';

/** Har soniyada yangilanadigan hozirgi vaqt (jonli taymerlar uchun) */
export default function useNow(ms = 1000) {
  const [now, setNow] = useState(() => Date.now());
  useEffect(() => {
    const id = setInterval(() => setNow(Date.now()), ms);
    return () => clearInterval(id);
  }, [ms]);
  return now;
}
