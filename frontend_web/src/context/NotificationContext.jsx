// frontend_web/src/context/NotificationContext.jsx
/**
 * App-wide notification (toast) system for human-centered feedback.
 *
 * Replaces raw alert()/silent failures with consistent, dismissible toasts that
 * speak the clinician's language: signal-quality blocks, clinical overrides,
 * offline saves, cold-start retries, and upload success/failure.
 *
 * Usage:
 *   const notify = useNotify();
 *   notify.success('Recording saved');
 *   notify.error('Upload failed', { detail: err.message });
 *   const id = notify.loading('Waking up server…');  notify.dismiss(id);
 *   notify.warning('High heart rate detected', { title: 'Signal note', duration: 0 });
 */
import React, { createContext, useContext, useState, useCallback, useRef } from 'react';

const NotificationContext = createContext(null);

let _counter = 0;
const nextId = () => `n${Date.now()}_${_counter++}`;

const DEFAULT_DURATIONS = { success: 4000, info: 5000, warning: 8000, error: 10000, loading: 0 };

export const NotificationProvider = ({ children }) => {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    setToasts((prev) => prev.filter((t) => t.id !== id));
    if (timers.current[id]) {
      clearTimeout(timers.current[id]);
      delete timers.current[id];
    }
  }, []);

  const push = useCallback((type, message, opts = {}) => {
    const id = opts.id || nextId();
    const duration = opts.duration ?? DEFAULT_DURATIONS[type] ?? 5000;
    const toast = {
      id, type, message,
      title: opts.title,
      detail: opts.detail,
      action: opts.action,   // { label, onClick }
    };
    setToasts((prev) => {
      // If an id is reused (e.g. a loading toast becoming success), replace it.
      const without = prev.filter((t) => t.id !== id);
      return [...without, toast];
    });
    if (timers.current[id]) clearTimeout(timers.current[id]);
    if (duration > 0) {
      timers.current[id] = setTimeout(() => dismiss(id), duration);
    }
    return id;
  }, [dismiss]);

  // Convenience helpers. Each returns the toast id so callers can update/dismiss.
  const api = {
    notify: push,
    success: (msg, o) => push('success', msg, o),
    error: (msg, o) => push('error', msg, o),
    warning: (msg, o) => push('warning', msg, o),
    info: (msg, o) => push('info', msg, o),
    loading: (msg, o) => push('loading', msg, { duration: 0, ...o }),
    // Update an existing toast (e.g. turn a "loading" into a "success").
    update: (id, type, msg, o = {}) => push(type, msg, { ...o, id }),
    dismiss,
  };

  return (
    <NotificationContext.Provider value={api}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </NotificationContext.Provider>
  );
};

export const useNotify = () => {
  const ctx = useContext(NotificationContext);
  if (!ctx) throw new Error('useNotify must be used within a NotificationProvider');
  return ctx;
};

// ---------------------------------------------------------------------------
// Presentation
// ---------------------------------------------------------------------------
const ICONS = { success: '✅', error: '⛔', warning: '⚠️', info: 'ℹ️', loading: '⏳' };

const ToastViewport = ({ toasts, onDismiss }) => (
  <div className="toast-viewport" aria-live="polite" aria-atomic="false">
    {toasts.map((t) => (
      <div key={t.id} className={`toast toast-${t.type}`} role="status">
        <span className={`toast-icon ${t.type === 'loading' ? 'toast-spin' : ''}`}>{ICONS[t.type]}</span>
        <div className="toast-body">
          {t.title && <div className="toast-title">{t.title}</div>}
          <div className="toast-message">{t.message}</div>
          {t.detail && <div className="toast-detail">{t.detail}</div>}
          {t.action && (
            <button
              className="toast-action"
              onClick={() => { t.action.onClick?.(); onDismiss(t.id); }}
            >
              {t.action.label}
            </button>
          )}
        </div>
        {t.type !== 'loading' && (
          <button className="toast-close" aria-label="Dismiss" onClick={() => onDismiss(t.id)}>×</button>
        )}
      </div>
    ))}
  </div>
);

export default NotificationContext;
