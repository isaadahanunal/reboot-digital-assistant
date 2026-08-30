import { useState } from 'react';
import Icon from '../components/Icon.jsx';
import Note from '../components/Note.jsx';
import { GOALS, TRIGGERS } from '../format.js';

/* First-run setup. Everything the app used to interrupt you for mid-task — your
   goal, where the numbers come from, the API key, the consent — is asked once,
   here, in order, with every step skippable. Nothing in this flow is a popup and
   nothing blocks: skipping all three still lands you in a working app. */
export default function Onboarding({ profile, saveProfile,
                                    startCollector, collector, finish }) {
  const [step, setStep] = useState(0);
  const [draft, setDraft] = useState({ ...profile });
  const [busy, setBusy] = useState(false);

  const set = (patch) => setDraft((d) => ({ ...d, ...patch }));


  async function complete() {
    setBusy(true);
    try {
      await saveProfile({ ...draft, onboarded: true });
      // Reboot measures this computer and only this computer, so recording is not
      // a choice to be offered -- it is what the app is. Failing to start it must
      // not block setup, though; Settings can retry and will explain why.
      try { await startCollector(); } catch { /* surfaced on the Settings page */ }
      finish();
    } finally { setBusy(false); }
  }

  return (
    <div className="setup">
      <div className="setup-inner">
        <div className="steps" role="progressbar" aria-valuemin={1} aria-valuemax={2}
             aria-valuenow={step + 1} aria-label={`Setup step ${step + 1} of 2`}>
          {[0, 1].map((i) => <div key={i} className={i <= step ? 'done' : ''} />)}
        </div>

        {step === 0 && (
          <div className="card">
            <div>
              <div className="eyebrow">
                <Icon name="sparkle" size={13} />
                <span>Step 1 of 2 · Intent</span>
              </div>
              <h1>What are you trying to change?</h1>
              <p className="card-sub">
                Reboot only flags screen time that conflicts with what you say you want. Nothing here is
                permanent — you can adapt all of it later.
              </p>
            </div>

            <fieldset>
              <legend>Your primary goal</legend>
              <div className="chips">
                {GOALS.map((g) => (
                  <button key={g} type="button" aria-pressed={draft.goal === g} onClick={() => set({ goal: g })}>{g}</button>
                ))}
              </div>
            </fieldset>

            <fieldset>
              <legend>The hardest moment of the day</legend>
              <div className="chips">
                {TRIGGERS.map((t) => (
                  <button key={t} type="button" aria-pressed={draft.trigger === t} onClick={() => set({ trigger: t })}>{t}</button>
                ))}
              </div>
            </fieldset>

            <label className="field">
              <span className="lab">Context in your own words <span style={{ fontWeight: 400, color: 'var(--text-3)' }}>(optional)</span></span>
              <textarea value={draft.context} onChange={(e) => set({ context: e.target.value })}
                        placeholder="e.g. I open Instagram for a 5-minute break between work blocks and it turns into forty." />
              <span className="help">Emails, links, phone numbers and handles are stripped before this is ever sent.</span>
            </label>

            <div className="btnrow" style={{ justifyContent: 'flex-end' }}>
              <button type="button" className="btn primary" onClick={() => setStep(1)}>
                <span>Continue</span>
                <Icon name="arrow" size={18} />
              </button>
            </div>
          </div>
        )}

        {step === 1 && (
          <div className="card">
            <div>
              <div className="eyebrow">
                <Icon name="shield" size={13} />
                <span>Step 2 of 2 · Intelligence &amp; Privacy</span>
              </div>
              <h1>Coach engine &amp; Consent</h1>
              <p className="card-sub">
                Reboot works in full offline mode without any key. Adding a key enables personalized AI reasoning.
              </p>
            </div>


            <div>
              <label className="switch">
                <input type="checkbox" checked={draft.consent_analytics}
                       onChange={(e) => set({ consent_analytics: e.target.checked })} />
                <span>
                  <span className="t">Send aggregated daily stats to AI model</span>
                  <span className="d">
                    Totals, category minutes, top apps, pickups, busiest hours. Never raw event streams.
                  </span>
                </span>
              </label>
              <label className="switch">
                <input type="checkbox" checked={draft.consent_context}
                       onChange={(e) => set({ consent_context: e.target.checked })} />
                <span>
                  <span className="t">Also send free-text notes</span>
                  <span className="d">
                    Off by default. Redaction automatically cleans PII, but keeping it off provides maximum privacy.
                  </span>
                </span>
              </label>
            </div>

            <Note tone="info" title="Non-clinical educational tool">
              <p>Reboot provides digital habit guidance. It does not provide medical or psychiatric diagnoses.</p>
            </Note>

            <div className="btnrow" style={{ justifyContent: 'space-between' }}>
              <button type="button" className="btn quiet" onClick={() => setStep(0)}>
                <Icon name="back" size={18} />Back
              </button>
              <button type="button" className="btn primary" onClick={complete} disabled={busy}>
                {busy ? <span className="spin" /> : <Icon name="ok" size={18} />}
                <span>Start using Reboot</span>
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

// eslint-disable-next-line no-unused-vars
function CopyButton({ text }) {
  const [done, setDone] = useState(false);
  return (
    <button type="button" className="btn quiet sm"
            onClick={async () => {
              try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1800); }
              catch { /* clipboard blocked; the command is visible anyway */ }
            }}>
      <Icon name={done ? 'ok' : 'copy'} size={16} />{done ? 'Copied' : 'Copy'}
    </button>
  );
}
