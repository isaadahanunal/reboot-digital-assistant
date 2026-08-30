import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import Icon from './Icon.jsx';
import Note from './Note.jsx';

/* Live control for the sampler running inside the local server. It polls rather
   than pushing, because a stopped collector must never look like a running one:
   the card shows what the sampler can see *right now*, which is also the clearest
   way to demonstrate that it only ever sees an application name. */
export function useCollector(intervalMs = 5000) {
  const [state, setState] = useState(null);
  const timer = useRef(null);

  const refresh = async () => {
    try { setState(await api('/api/collector/status')); } catch { /* server restarting */ }
  };

  useEffect(() => {
    refresh();
    timer.current = setInterval(refresh, intervalMs);
    return () => clearInterval(timer.current);
  }, [intervalMs]);

  return [state, refresh];
}

export default function CollectorCard({ state, refresh, onData, compact = false }) {
  const [busy, setBusy] = useState(false);
  if (!state) return null;

  async function toggle() {
    setBusy(true);
    try {
      await api(state.running ? '/api/collector/stop' : '/api/collector/start',
                { method: 'POST', body: {} });
      await refresh();
      if (onData) await onData();
    } finally { setBusy(false); }
  }

  async function toggleDomains() {
    setBusy(true);
    try {
      await api('/api/settings', { method: 'POST', body: { capture_domains: !state.capture_domains } });
      if (state.running) {
        await api('/api/collector/stop', { method: 'POST', body: {} });
        await api('/api/collector/start', { method: 'POST', body: {} });
      }
      await refresh();
    } finally { setBusy(false); }
  }

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 'var(--s-3)' }}>
        <div className="grow">
          <h3>This computer</h3>
          <p className="card-sub" style={{ margin: 0 }}>
            {state.device} · {state.platform}
          </p>
        </div>
        <span className={`badge ${state.running ? 'good' : 'flat'}`}>
          <Icon name={state.running ? 'ok' : 'alert'} size={14} />
          {state.running ? 'Recording' : 'Stopped'}
        </span>
      </div>

      {state.running && (
        <div className="cmd" style={{ marginBottom: 'var(--s-3)' }}>
          <code>
            {state.idle
              ? 'idle — nothing is being counted'
              : `in front right now: ${state.current_app || 'unknown'}`}
          </code>
          <span className="badge flat">{state.sessions_captured} saved</span>
        </div>
      )}

      {state.blocked_reason && (
        <Note tone="alert" title="Another Reboot is already recording">{state.blocked_reason}</Note>
      )}

      {state.permission_hint && (
        <Note tone="warn" title="Cannot read the frontmost app">{state.permission_hint}</Note>
      )}

      <div className="btnrow" style={{ marginTop: 'var(--s-3)' }}>
        <button type="button" className={`btn ${state.running ? 'quiet' : 'primary'}`}
                onClick={toggle} disabled={busy}>
          {busy ? <span className="spin" /> : <Icon name={state.running ? 'alert' : 'laptop'} size={18} />}
          {state.running ? 'Stop recording' : 'Start recording on this computer'}
        </button>
      </div>

      {!compact && (
        <>
          <label className="switch" style={{ marginTop: 'var(--s-4)' }}>
            <input type="checkbox" checked={state.capture_domains} onChange={toggleDomains} disabled={busy} />
            <span>
              <span className="t">Also record browser host names</span>
              <span className="d">
                Off by default. Records <code>youtube.com</code>, never the full URL, the page title or its
                content — enough to tell "browsing" apart from "watching", which plain "Chrome" cannot.
              </span>
            </span>
          </label>

          <p className="hint" style={{ marginTop: 'var(--s-3)' }}>
            Recording runs inside the local server, so it keeps going when you close this tab and restarts
            with the server. It never records keystrokes, window titles, URLs, screenshots or file names,
            and time spent idle for more than two minutes is discarded rather than counted.
          </p>
        </>
      )}
    </div>
  );
}
