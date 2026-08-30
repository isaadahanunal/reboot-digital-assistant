import { useState } from 'react';
import CollectorCard from '../components/CollectorCard.jsx';
import Icon from '../components/Icon.jsx';
import Note from '../components/Note.jsx';

/* Deliberately free of plumbing. The API key, the provider list and the model id
   are configuration, not decisions a person using a well-being app should be
   asked to make mid-task; they live in .env and are documented in the README.
   What stays here is the one question that is genuinely the user's: should a
   model read my numbers at all, or should the offline coach do it. */
export default function Settings({ settings, saveSettings, refresh, collector, refreshCollector, onData }) {
  const [busy, setBusy] = useState(false);
  if (!settings) return <p className="hint">Loading settings…</p>;

  const usingAi = settings.selected !== 'offline';
  const which = settings.selected === 'anthropic' ? 'anthropic' : 'gemini';
  const keyReady = which === 'anthropic' ? settings.anthropic_key_set : settings.gemini_key_set;

  async function setEngine(useAi) {
    setBusy(true);
    try {
      await saveSettings({ provider: useAi ? 'gemini' : 'offline' });
      await refresh();
    } finally { setBusy(false); }
  }

  return (
    <div className="page stack">
      <div className="page-head">
        <div className="eyebrow">
          <Icon name="settings" size={14} />
          <span>Settings</span>
        </div>
        <h1>Measurement &amp; coach</h1>
        <p>
          Reboot measures this computer and nothing else. There is no account, no sync and no second
          device to manage.
        </p>
      </div>

      <CollectorCard state={collector} refresh={refreshCollector} onData={onData} />

      <div className="card">
        <div className="row" style={{ gap: 'var(--s-2)', marginBottom: 'var(--s-3)' }}>
          <Icon name="sparkle" size={18} />
          <h3 style={{ margin: 0, flex: 1 }}>Your coach</h3>
          <span className={`badge ${usingAi && keyReady ? 'good' : 'flat'}`}>
            <Icon name={usingAi && keyReady ? 'ok' : 'alert'} size={14} />
            {usingAi ? (keyReady ? 'AI coach ready' : 'AI coach not connected') : 'Offline coach'}
          </span>
        </div>

        <label className="switch">
          <input type="checkbox" checked={usingAi} disabled={busy}
                 onChange={(e) => setEngine(e.target.checked)} />
          <span>
            <span className="t">Let an AI model write my digests and plans</span>
            <span className="d">
              Turn this off and Reboot uses its built-in coach instead: no model, nothing leaves your
              machine, and every suggestion is labelled as rule-based rather than AI-written.
            </span>
          </span>
        </label>

        {usingAi && !keyReady && (
          <div style={{ marginTop: 'var(--s-4)' }}>
            <Note tone="warn" title="No coach connected yet">
              Reboot needs a Google AI Studio key to write digests. Add it once to the
              <code> .env</code> file next to <code>run.sh</code> and restart — the README has the two
              lines. Until then the offline coach still works.
            </Note>
          </div>
        )}
      </div>
    </div>
  );
}
