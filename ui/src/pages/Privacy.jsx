import { useEffect, useState } from 'react';
import ConfirmButton from '../components/ConfirmButton.jsx';
import Icon from '../components/Icon.jsx';
import Note from '../components/Note.jsx';
import { GOALS, TRIGGERS } from '../format.js';

export default function Privacy({ profile, saveProfile, preview, refreshPreview, eraseAll }) {
  const [draft, setDraft] = useState(profile);
  const [saved, setSaved] = useState(false);
  const set = (patch) => { setDraft((d) => ({ ...d, ...patch })); setSaved(false); };

  useEffect(() => { setDraft(profile); }, [profile]);

  async function save() {
    await saveProfile(draft);
    await refreshPreview();
    setSaved(true);
    setTimeout(() => setSaved(false), 2400);
  }

  return (
    <div className="page stack">
      <div className="page-head">
        <div className="eyebrow">
          <Icon name="shield" size={14} />
          <span>Local-First &amp; Transparent</span>
        </div>
        <h1>Privacy &amp; Data Transparency</h1>
        <p>
          Collection, storage and every calculation happen directly on your machine in local SQLite.
          The single outbound request is the AI coach generation you initiate yourself.
        </p>
      </div>

      <div className="grid two">
        <div className="card" style={{ borderTop: '4px solid var(--good)' }}>
          <div className="row" style={{ gap: 'var(--s-2)', color: 'var(--good)', marginBottom: 'var(--s-2)' }}>
            <Icon name="ok" size={20} />
            <h3 style={{ margin: 0, color: 'inherit' }}>Collected &amp; Processed Locally</h3>
          </div>
          <ul style={{ paddingLeft: 20, color: 'var(--text-2)', marginTop: 'var(--s-3)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <li>Foreground application name and active duration</li>
            <li>Browser host names — strictly opt-in with <code>--capture-domains</code></li>
            <li>Your goals, reflection check-ins, and target preferences</li>
          </ul>
        </div>
        <div className="card" style={{ borderTop: '4px solid var(--alert)' }}>
          <div className="row" style={{ gap: 'var(--s-2)', color: 'var(--alert)', marginBottom: 'var(--s-2)' }}>
            <Icon name="alert" size={20} />
            <h3 style={{ margin: 0, color: 'inherit' }}>Never Collected or Stored</h3>
          </div>
          <ul style={{ paddingLeft: 20, color: 'var(--text-2)', marginTop: 'var(--s-3)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            <li>Keystrokes, screenshots, camera, microphone, or window contents</li>
            <li>Full URLs, file names, personal messages, or contact lists</li>
            <li>Any activity whatsoever when the agent is turned off</li>
          </ul>
        </div>
      </div>

      <div className="card">
        <div className="row" style={{ gap: 'var(--s-2)', marginBottom: 'var(--s-1)' }}>
          <Icon name="today" size={18} />
          <h3 style={{ margin: 0 }}>Your Profile &amp; Preferences</h3>
        </div>
        <p className="card-sub">Used to tailor advice. Only the specific fields you consent to are ever included in prompts.</p>

        <fieldset style={{ marginBottom: 'var(--s-4)' }}>
          <legend>Primary goal</legend>
          <div className="chips">
            {GOALS.map((g) => (
              <button key={g} type="button" aria-pressed={draft.goal === g} onClick={() => set({ goal: g })}>{g}</button>
            ))}
          </div>
        </fieldset>

        <label className="field">
          <span className="lab">Hardest moment</span>
          <select value={draft.trigger} onChange={(e) => set({ trigger: e.target.value })}>
            {TRIGGERS.map((t) => <option key={t}>{t}</option>)}
          </select>
        </label>

        <label className="field">
          <span className="lab">Context in your own words</span>
          <textarea value={draft.context} onChange={(e) => set({ context: e.target.value })}
                    placeholder="Optional. What actually happens, in your words." />
          <span className="help">Emails, links, phone numbers, handles and dates are stripped before this is sent.</span>
        </label>

        <div className="grid three">
          <label className="field">
            <span className="lab">Tone</span>
            <select value={draft.tone} onChange={(e) => set({ tone: e.target.value })}>
              <option value="gentle">Gentle</option>
              <option value="direct">Direct</option>
            </select>
          </label>
          <label className="field">
            <span className="lab">Coach language</span>
            <select value={draft.language} onChange={(e) => set({ language: e.target.value })}>
              <option value="en">English</option>
              <option value="tr">Türkçe</option>
            </select>
          </label>
          <label className="field">
            <span className="lab">Daily target (minutes)</span>
            <input type="number" min="30" max="960" step="10" value={draft.daily_target_minutes}
                   onChange={(e) => set({ daily_target_minutes: Number(e.target.value) || 180 })} />
          </label>
          <label className="field">
            <span className="lab">Age band</span>
            <select value={draft.age_band} onChange={(e) => set({ age_band: e.target.value })}>
              <option value="undisclosed">Prefer not to say</option>
              <option value="under_18">Under 18</option>
              <option value="18_24">18–24</option>
              <option value="25_39">25–39</option>
              <option value="40_plus">40+</option>
            </select>
            <span className="help">Only a coarse "possible minor" flag is ever sent, never your exact age.</span>
          </label>
        </div>

        <h3 style={{ marginTop: 'var(--s-4)' }}>Consent</h3>
        <p className="card-sub">Both are off until you turn them on, and both can be withdrawn here.</p>
        <label className="switch">
          <input type="checkbox" checked={draft.consent_analytics}
                 onChange={(e) => set({ consent_analytics: e.target.checked })} />
          <span>
            <span className="t">Send my aggregated daily metrics to the AI provider</span>
            <span className="d">Required for AI generation. Without it the app still works in rule-based offline mode.</span>
          </span>
        </label>
        <label className="switch">
          <input type="checkbox" checked={draft.consent_context}
                 onChange={(e) => set({ consent_context: e.target.checked })} />
          <span>
            <span className="t">Also send my free-text context</span>
            <span className="d">Off by default. Free text is where sensitive detail leaks; redaction reduces that risk but does not eliminate it.</span>
          </span>
        </label>
        <label className="switch">
          <input type="checkbox" checked={draft.share_app_names}
                 onChange={(e) => set({ share_app_names: e.target.checked })} />
          <span>
            <span className="t">Send real app names</span>
            <span className="d">Turn off to send categories only — "social app A" instead of "Instagram". Advice gets slightly less specific.</span>
          </span>
        </label>

        <div className="btnrow" style={{ marginTop: 'var(--s-4)' }}>
          <button type="button" className="btn primary" onClick={save}>
            <Icon name={saved ? 'ok' : 'ok'} size={18} />{saved ? 'Saved' : 'Save profile'}
          </button>
        </div>
      </div>

      <div className="card">
        <div className="row" style={{ marginBottom: 'var(--s-3)' }}>
          <div className="grow">
            <h3>Exactly what would be sent</h3>
            <p className="card-sub" style={{ margin: 0 }}>
              Built by the same code path the coach uses, so this is the payload, not a description of it.
            </p>
          </div>
          <button type="button" className="btn quiet sm" onClick={refreshPreview}>
            <Icon name="refresh" size={16} />Refresh
          </button>
        </div>
        <pre className="json">{preview ? JSON.stringify(preview, null, 2) : 'Loading…'}</pre>
      </div>

      <div className="card">
        <h3>Delete everything</h3>
        <p className="card-sub">
          Removes every session, generated plan and check-in from this machine. Immediate and irreversible.
        </p>
        <ConfirmButton confirmLabel="Yes, erase everything" onConfirm={eraseAll}>
          Erase all my data
        </ConfirmButton>
      </div>

      <Note tone="info" title="Not a medical tool">
        Reboot gives general digital-habit guidance. It does not diagnose anything. If screen use is
        tangled up with your sleep, mood, studies or relationships, please talk to a qualified person.
      </Note>
    </div>
  );
}
