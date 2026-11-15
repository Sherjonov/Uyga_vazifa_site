import { useEffect, useRef } from 'react';
import './OtpInput.css';

/** 6 ta alohida katak. Paste, backspace, strelkalar va avtomatik to'ldirish (SMS/email kodi) ishlaydi. */
export default function OtpInput({ value = '', onChange, length = 6, disabled, error, autoFocus = true }) {
  const refs = useRef([]);
  const digits = Array.from({ length }, (_, i) => value[i] || '');

  useEffect(() => { if (autoFocus) refs.current[0]?.focus(); }, [autoFocus]);

  const set = (idx, ch) => {
    const arr = [...digits];
    arr[idx] = ch;
    onChange(arr.join('').slice(0, length));
  };

  const onInput = (i, e) => {
    const raw = e.target.value.replace(/\D/g, '');
    if (!raw) return set(i, '');
    if (raw.length > 1) {
      // brauzer avtomatik to'ldirsa (one-time-code) yoki paste qilinsa
      const next = (value.slice(0, i) + raw).slice(0, length);
      onChange(next);
      refs.current[Math.min(next.length, length - 1)]?.focus();
      return;
    }
    set(i, raw);
    if (i < length - 1) refs.current[i + 1]?.focus();
  };

  const onKeyDown = (i, e) => {
    if (e.key === 'Backspace' && !digits[i] && i > 0) { e.preventDefault(); set(i - 1, ''); refs.current[i - 1]?.focus(); }
    if (e.key === 'ArrowLeft' && i > 0) refs.current[i - 1]?.focus();
    if (e.key === 'ArrowRight' && i < length - 1) refs.current[i + 1]?.focus();
  };

  const onPaste = e => {
    const text = (e.clipboardData.getData('text') || '').replace(/\D/g, '').slice(0, length);
    if (!text) return;
    e.preventDefault();
    onChange(text);
    refs.current[Math.min(text.length, length - 1)]?.focus();
  };

  return (
    <div className={`otp ${error ? 'otp-error' : ''}`} onPaste={onPaste}>
      {digits.map((d, i) => (
        <input
          key={i}
          ref={el => (refs.current[i] = el)}
          className={`otp-cell ${d ? 'filled' : ''}`}
          value={d}
          inputMode="numeric"
          pattern="[0-9]*"
          maxLength={i === 0 ? length : 1}
          autoComplete={i === 0 ? 'one-time-code' : 'off'}
          name={i === 0 ? 'otp' : undefined}
          disabled={disabled}
          aria-label={`${i + 1}`}
          onChange={e => onInput(i, e)}
          onKeyDown={e => onKeyDown(i, e)}
          onFocus={e => e.target.select()}
        />
      ))}
    </div>
  );
}
