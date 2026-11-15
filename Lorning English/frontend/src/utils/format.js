const LOCALES = { uz: 'uz-UZ', en: 'en-GB', ru: 'ru-RU' };

const parse = v => (v ? new Date(v) : null);

export const fmtDate = (v, lang = 'uz') => {
  const d = parse(v);
  if (!d || Number.isNaN(d.getTime())) return '';
  return d.toLocaleDateString(LOCALES[lang] || 'en-GB', { day: '2-digit', month: 'short', year: 'numeric' });
};

export const fmtDateTime = (v, lang = 'uz') => {
  const d = parse(v);
  if (!d || Number.isNaN(d.getTime())) return '';
  return d.toLocaleString(LOCALES[lang] || 'en-GB', { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' });
};

const UZ_MON = ['yan', 'fev', 'mar', 'apr', 'may', 'iyun', 'iyul', 'avg', 'sen', 'okt', 'noy', 'dek'];

/** Qisqa sana-vaqt: uz "13-noy, 14:30", boshqa tillarda "13 Nov, 14:30" */
export const fmtShort = (v, lang = 'uz') => {
  const d = parse(v);
  if (!d || Number.isNaN(d.getTime())) return '';
  const p = n => String(n).padStart(2, '0');
  const hm = `${p(d.getHours())}:${p(d.getMinutes())}`;
  if (lang === 'uz') return `${d.getDate()}-${UZ_MON[d.getMonth()]}, ${hm}`;
  return `${d.toLocaleDateString(LOCALES[lang] || 'en-GB', { day: 'numeric', month: 'short' })}, ${hm}`;
};

export const fmtTime = (v, lang = 'uz') => {
  const d = parse(v);
  if (!d || Number.isNaN(d.getTime())) return '';
  return d.toLocaleTimeString(LOCALES[lang] || 'en-GB', { hour: '2-digit', minute: '2-digit' });
};

/** Sekundni "2 kun 3 soat" ko'rinishiga o'giradi (t: i18n funksiyasi) */
export const fmtDuration = (sec, t) => {
  let s = Math.max(0, Math.floor(sec));
  const d = Math.floor(s / 86400);
  s -= d * 86400;
  const h = Math.floor(s / 3600);
  s -= h * 3600;
  const m = Math.floor(s / 60);
  if (d > 0) return `${d} ${t('time.d')} ${h} ${t('time.h')}`;
  if (h > 0) return `${h} ${t('time.h')} ${m} ${t('time.m')}`;
  return `${Math.max(m, 0)} ${t('time.m')}`;
};

export const initials = name =>
  (name || '?')
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map(w => w[0].toUpperCase())
    .join('');

export const num = (v, d = 1) => (v == null || Number.isNaN(Number(v)) ? '–' : Number(Number(v).toFixed(d)));

/** datetime-local qiymatini UTC ISO ga o'giradi */
export const localToIso = v => (v ? new Date(v).toISOString() : '');

export const homeFor = user => {
  if (!user) return '/login';
  if (!user.onboarded) return '/onboarding';
  if (user.role === 'teacher') return '/teacher/students';
  return '/student/home';
};

export const todayStr = () => {
  const d = new Date();
  const p = n => String(n).padStart(2, '0');
  return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}`;
};

/** To'liq sana va vaqt, soniyalargacha: 10.11.2026 21:24:05 */
export const fmtFull = (v, lang = 'uz') => {
  const d = v ? new Date(v) : null;
  if (!d || Number.isNaN(d.getTime())) return '–';
  return d.toLocaleString(LOCALES[lang] || 'en-GB', { day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit', hour12: false });
};

/** 60000 -> "60 000" */
export const fmtMoney = n => String(Math.round(Number(n) || 0)).replace(/\B(?=(\d{3})+(?!\d))/g, ' ');

/** Sekundlarni "12 kun 03:25:10" ko'rinishida (t: i18n funksiyasi) */
export const fmtCountdown = (sec, t) => {
  let s = Math.max(0, Math.floor(sec));
  const d = Math.floor(s / 86400);
  s -= d * 86400;
  const p = n => String(n).padStart(2, '0');
  const clock = `${p(Math.floor(s / 3600))}:${p(Math.floor((s % 3600) / 60))}:${p(s % 60)}`;
  return d > 0 ? `${d} ${t('time.d')} ${clock}` : clock;
};
