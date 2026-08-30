import { useEffect, useRef, useState } from 'react';
import Icon from './Icon.jsx';
import Note from './Note.jsx';

export default function GenerateCard({ label, againLabel, hint, onGenerate, onGrantConsent, hasResult, children }) {
  const [busy, setBusy] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState(null);
  const timer = useRef(null);

  useEffect(() => () => clearInterval(timer.current), []);

  async function run() {
    setBusy(true);
    setError(null);
    setSeconds(0);
    const started = Date.now();
    timer.current = setInterval(() => setSeconds(Math.round((Date.now() - started) / 1000)), 250);
    try {
      await onGenerate();
    } catch (err) {
      setError(err);
    } finally {
      clearInterval(timer.current);
      setBusy(false);
    }
  }

  async function grant() {
    setError(null);
    await onGrantConsent();
    run();
  }

  return (
    <div className="stack">
      <div className="card" style={{
        background: busy ? 'var(--surface-2)' : 'var(--surface)',
        borderColor: busy ? 'var(--accent)' : (hasResult ? 'var(--border)' : 'var(--accent-border)'),
        boxShadow: busy ? '0 0 25px rgba(99, 102, 241, 0.2)' : 'var(--shadow-1)',
      }}>
        <button
          type="button"
          className="btn primary block"
          onClick={run}
          disabled={busy}
          style={{
            minHeight: '48px',
            fontSize: '15px',
            boxShadow: busy ? 'none' : '0 4px 14px rgba(79, 70, 229, 0.4)',
          }}>
          {busy ? <span className="spin" /> : <Icon name="sparkle" size={19} />}
          {busy ? `Coach is analyzing your metrics… ${seconds}s` : (hasResult ? againLabel : label)}
        </button>
        <p className="hint" style={{ margin: 'var(--s-3) 0 0', textAlign: 'center', fontSize: '13px' }}>
          {busy
            ? 'Deterministic metrics aggregated locally. Processing AI reasoning pass...'
            : hint}
        </p>
      </div>

      {error?.kind === 'consent' && (
        <div className="card" style={{ borderLeft: '4px solid var(--accent)' }}>
          <div className="row" style={{ gap: 'var(--s-2)', marginBottom: 'var(--s-2)' }}>
            <Icon name="shield" size={20} />
            <h3 style={{ margin: 0 }}>Consent Required for AI Analysis</h3>
          </div>
          <p className="card-sub" style={{ marginBottom: 'var(--s-3)' }}>
            Reboot only sends aggregated statistics (daily minutes, category breakdown, top apps, pickups,
            peak hours). It <b>never</b> transmits raw keystrokes, window titles, screenshots, or browsing history.
          </p>
          <div className="btnrow">
            <button type="button" className="btn primary" onClick={grant}>
              <Icon name="ok" size={18} />Allow &amp; Continue
            </button>
            <a className="btn quiet" href="#privacy">
              <Icon name="eye" size={16} />Preview Payload
            </a>
          </div>
        </div>
      )}

      {error?.kind === 'no_key' && (
        <Note tone="warn" title="No coach engine connected yet">
          <p style={{ margin: '0 0 var(--s-3)' }}>{error.message}</p>
          <a className="btn quiet sm" href="#settings"><Icon name="settings" size={16} />Configure API key in settings</a>
        </Note>
      )}

      {error && !['consent', 'no_key'].includes(error.kind) && (
        <Note tone="alert" title="Generation failed">
          {error.message}
          {error.retryable && ' You can retry — transient rate limits or cold starts resolve automatically.'}
        </Note>
      )}

      {children}
    </div>
  );
}
