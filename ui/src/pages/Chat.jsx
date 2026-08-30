import { useEffect, useRef, useState } from 'react';
import { api } from '../api.js';
import { SupportCard } from '../components/CoachMeta.jsx';
import ConfirmButton from '../components/ConfirmButton.jsx';
import Icon from '../components/Icon.jsx';
import Note from '../components/Note.jsx';
import RichText from '../components/RichText.jsx';

const STARTERS = [
  'What did my screen time look like today?',
  'Why is the evening so hard for me?',
  'Give me one thing to try tonight.',
  "I skipped yesterday's plan. What now?",
];

export default function Chat({ onGrantConsent }) {
  const [messages, setMessages] = useState([]);
  const [draft, setDraft] = useState('');
  const [busy, setBusy] = useState(false);
  const [seconds, setSeconds] = useState(0);
  const [error, setError] = useState(null);
  const [support, setSupport] = useState(null);
  const endRef = useRef(null);
  const timer = useRef(null);

  useEffect(() => {
    api('/api/chat').then((d) => setMessages(d.messages)).catch(() => {});
    return () => clearInterval(timer.current);
  }, []);

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }); }, [messages, busy]);

  async function send(text) {
    const message = (text ?? draft).trim();
    if (!message || busy) return;
    setDraft('');
    setError(null);
    setSupport(null);
    setMessages((m) => [...m, { role: 'user', content: message }]);
    setBusy(true);
    setSeconds(0);
    const started = Date.now();
    timer.current = setInterval(() => setSeconds(Math.round((Date.now() - started) / 1000)), 250);
    try {
      const res = await api('/api/chat', { method: 'POST', body: { message } });
      if (res.kind === 'support_card') setSupport(res.content);
      else setMessages((m) => [...m, { role: 'assistant', content: res.content, meta: res.meta }]);
    } catch (err) {
      setError(err);
      // Keep the user's own words on screen; losing what you typed to an error is its own insult.
      setDraft(message);
      setMessages((m) => m.slice(0, -1));
    } finally {
      clearInterval(timer.current);
      setBusy(false);
    }
  }

  return (
    <div className="page stack">
      <div className="page-head row">
        <div className="grow">
          <div className="eyebrow">Talk it through</div>
          <h1>Coach chat</h1>
          <p>
            The same coach that writes your digests, in conversation. It can see the numbers this
            computer measured — today&apos;s totals, your week, your current plan and which actions you
            ticked off — and nothing else about you.
          </p>
        </div>
        {messages.length > 0 && (
          <ConfirmButton icon="trash" confirmLabel="Yes, clear it"
                         onConfirm={async () => { await api('/api/chat/clear', { method: 'POST', body: {} }); setMessages([]); }}>
            Clear chat
          </ConfirmButton>
        )}
      </div>

      <div className="card">
        {messages.length === 0 && !support && (
          <div style={{ marginBottom: 'var(--s-4)' }}>
            <p className="card-sub">Not sure where to start?</p>
            <div className="chips">
              {STARTERS.map((s) => (
                <button key={s} type="button" onClick={() => send(s)} disabled={busy}>{s}</button>
              ))}
            </div>
          </div>
        )}

        <div className="chat-log">
          {messages.map((m, i) => (
            <div key={i} className={`bubble ${m.role}`}>
              <div className="who">{m.role === 'user' ? 'You' : 'Reboot'}</div>
              <div className="what">
                {m.role === 'assistant' ? <RichText text={m.content} /> : m.content}
              </div>
            </div>
          ))}
          {busy && (
            <div className="bubble assistant">
              <div className="who">Reboot</div>
              <div className="what hint"><span className="spin" /> thinking… {seconds}s</div>
            </div>
          )}
          <div ref={endRef} />
        </div>

        {support && <SupportCard card={support} />}

        {error?.kind === 'consent' && (
          <Note tone="warn" title="One permission first">
            <p style={{ margin: '0 0 var(--s-3)' }}>
              To answer with your own numbers, the coach needs permission to send the aggregated
              measurements — totals, categories, top apps. Never a raw activity log.
            </p>
            <button type="button" className="btn quiet sm"
                    onClick={async () => { await onGrantConsent(); setError(null); }}>
              <Icon name="ok" size={16} />Allow and continue
            </button>
          </Note>
        )}
        {error?.kind === 'offline_chat' && (
          <Note tone="info" title="Chat needs the AI coach">
            <p style={{ margin: '0 0 var(--s-3)' }}>{error.message}</p>
            <a className="btn quiet sm" href="#settings"><Icon name="settings" size={16} />Open settings</a>
          </Note>
        )}
        {error?.kind === 'no_key' && (
          <Note tone="warn" title="No coach connected">
            <p style={{ margin: '0 0 var(--s-3)' }}>{error.message}</p>
            <a className="btn quiet sm" href="#settings"><Icon name="settings" size={16} />Open settings</a>
          </Note>
        )}
        {error && !['consent', 'offline_chat', 'no_key'].includes(error.kind) && (
          <Note tone="alert" title="That message did not go through">{error.message}</Note>
        )}

        <form className="composer" onSubmit={(e) => { e.preventDefault(); send(); }}>
          <label htmlFor="chat-input" className="sr-only">Your message</label>
          <textarea id="chat-input" value={draft} rows={2} disabled={busy}
                    placeholder="Ask about your week, or tell it what actually happened…"
                    onChange={(e) => setDraft(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send(); }
                    }} />
          <button type="submit" className="btn primary" disabled={busy || !draft.trim()}>
            <Icon name="arrow" size={18} /><span className="sr-only">Send</span>
          </button>
        </form>
        <p className="hint" style={{ margin: 'var(--s-3) 0 0' }}>
          Enter sends, Shift+Enter adds a line. This is general habit guidance, not medical advice.
        </p>
      </div>
    </div>
  );
}
