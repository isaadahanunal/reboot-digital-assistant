import { useCallback, useEffect, useState } from 'react';
import { api } from './api.js';
import Icon from './components/Icon.jsx';
import Note from './components/Note.jsx';
import Sidebar from './components/Sidebar.jsx';
import { useCollector } from './components/CollectorCard.jsx';
import { useTheme } from './useTheme.js';
import Chat from './pages/Chat.jsx';
import CheckIn from './pages/CheckIn.jsx';
import Onboarding from './pages/Onboarding.jsx';
import Plan from './pages/Plan.jsx';
import Privacy from './pages/Privacy.jsx';
import Prompts from './pages/Prompts.jsx';
import Settings from './pages/Settings.jsx';
import Today from './pages/Today.jsx';

const ROUTES = ['today', 'chat', 'plan', 'checkin', 'privacy', 'prompts', 'settings'];
const TITLES = {
  today: 'Today', chat: 'Chat', plan: 'Plan', checkin: 'Check-in',
  privacy: 'Privacy', prompts: 'Prompts', settings: 'Settings',
};

function useHashRoute() {
  const read = () => {
    const hash = window.location.hash.replace('#', '');
    return ROUTES.includes(hash) ? hash : 'today';
  };
  const [route, setRoute] = useState(read);
  useEffect(() => {
    const onChange = () => { setRoute(read()); window.scrollTo({ top: 0 }); };
    window.addEventListener('hashchange', onChange);
    return () => window.removeEventListener('hashchange', onChange);
  }, []);
  return route;
}

export default function App() {
  const route = useHashRoute();
  const [theme, setTheme] = useTheme();
  const [collector, refreshCollector] = useCollector();

  const [status, setStatus] = useState(null);
  const [profile, setProfile] = useState(null);
  const [settings, setSettings] = useState(null);
  const [metrics, setMetrics] = useState(null);
  const [dates, setDates] = useState([]);
  const [date, setDate] = useState(null);
  const [digest, setDigest] = useState(null);
  const [plan, setPlan] = useState(null);
  const [checkins, setCheckins] = useState([]);
  const [preview, setPreview] = useState(null);
  // Setup runs on every start, not just the first: this is session state, not the
  // persisted profile.onboarded flag, so a reload always walks the steps again.
  const [setupDone, setSetupDone] = useState(false);
  const [bootError, setBootError] = useState(null);

  const loadDay = useCallback(async (key) => {
    const data = await api(`/api/metrics${key ? `?date=${key}` : ''}`);
    setMetrics(data.metrics);
    setDate(data.metrics.date_key);
    try {
      setDigest(await api(`/api/coach/latest?kind=daily_digest&date=${data.metrics.date_key}`));
    } catch { setDigest(null); }
  }, []);

  const boot = useCallback(async (keepDate) => {
    const s = await api('/api/status');
    setStatus(s);
    setProfile(s.profile);
    setDates(s.dates);
    setSettings(await api('/api/settings'));
    setCheckins((await api('/api/checkins')).checkins);
    await loadDay(keepDate || s.dates[0] || s.today);
    try { setPlan(await api('/api/coach/latest?kind=weekly_plan')); } catch { setPlan(null); }
  }, [loadDay]);

  useEffect(() => { boot().catch(setBootError); }, [boot]);

  // While the collector is recording, the numbers on screen go stale within a
  // minute. Refresh the day quietly rather than making the user reload.
  useEffect(() => {
    if (!collector?.running || route !== 'today' || !date) return undefined;
    const id = setInterval(() => { loadDay(date).catch(() => {}); }, 30000);
    return () => clearInterval(id);
  }, [collector?.running, route, date, loadDay]);

  const refreshPreview = useCallback(async () => {
    try {
      setPreview(await api(`/api/privacy/preview?kind=daily_digest&date=${date || ''}`));
    } catch (err) { setPreview({ error: err.message }); }
  }, [date]);

  useEffect(() => { if (route === 'privacy' && date) refreshPreview(); }, [route, date, refreshPreview]);

  const saveProfile = useCallback(async (next) => {
    setProfile(await api('/api/profile', { method: 'POST', body: next }));
  }, []);

  const saveSettings = useCallback(async (body) => {
    setSettings(await api('/api/settings', { method: 'POST', body }));
    setStatus((s) => (s ? { ...s, provider: { ...s.provider } } : s));
  }, []);

  const grantConsent = useCallback(async () => {
    await saveProfile({ ...profile, consent_analytics: true });
  }, [profile, saveProfile]);

  const generateDaily = useCallback(async () => {
    setDigest(await api('/api/coach/daily', { method: 'POST', body: { date_key: date } }));
  }, [date]);

  const generateWeekly = useCallback(async () => {
    setPlan(await api('/api/coach/weekly', { method: 'POST', body: { date_key: date } }));
  }, [date]);

  const onCheck = useCallback(async (dateKey, actionId, statusValue) => {
    const res = await api('/api/checkin', {
      method: 'POST', body: { date_key: dateKey, action_id: actionId, status: statusValue, note: '' },
    });
    setCheckins(res.checkins);
  }, []);

  const seedDemo = useCallback(async () => {
    await api('/api/demo/seed', { method: 'POST', body: {} });
    await boot();
  }, [boot]);

  const eraseAll = useCallback(async () => {
    await api('/api/privacy/erase', { method: 'POST', body: {} });
    setDigest(null); setPlan(null); setPreview(null);
    await boot();
  }, [boot]);

  if (bootError) {
    return (
      <main style={{ padding: 'var(--s-6)' }}>
        <Note tone="alert" title="Could not reach the local server">
          {bootError.message}. Start it with <code>./run.sh</code> from the <code>reboot</code> folder.
        </Note>
      </main>
    );
  }

  if (!status || !profile) {
    return <main style={{ padding: 'var(--s-6)' }}><p className="hint">Starting Reboot…</p></main>;
  }

  if (!setupDone) {
    return (
      <Onboarding
        profile={profile}
        saveProfile={saveProfile}
        startCollector={async () => { await api('/api/collector/start', { method: 'POST', body: {} }); await refreshCollector(); }}
        collector={collector}
        finish={() => { setSetupDone(true); boot(); }}
      />
    );
  }

  return (
    <>
      <a className="skip" href="#main-content">Skip to content</a>
      <div className="app">
        <Sidebar route={route} theme={theme} setTheme={setTheme} />
        <main id="main-content">
          <div className="topbar-mobile">
            <span className="mark" aria-hidden="true"
                  style={{ width: 32, height: 32, borderRadius: 10, background: 'var(--accent)',
                           color: 'var(--on-accent)', display: 'grid', placeItems: 'center', fontWeight: 800 }}>R</span>
            <b className="grow">{TITLES[route]}</b>
            <a className="icon-btn" href="#settings"
               aria-current={route === 'settings' ? 'page' : undefined} aria-label="Settings">
              <Icon name="settings" size={18} />
            </a>
            <div className="theme" role="group" aria-label="Colour theme">
              {[['light', 'sun', 'Light'], ['system', 'monitor', 'System'], ['dark', 'moon', 'Dark']].map(
                ([value, icon, label]) => (
                  <button key={value} type="button" aria-pressed={theme === value}
                          onClick={() => setTheme(value)} title={label}>
                    <Icon name={icon} size={16} />
                    <span className="sr-only">{label}</span>
                  </button>
                ))}
            </div>
          </div>

          <div className="page" hidden={route !== 'today'}>
            {route === 'today' && (
              <Today status={status} metrics={metrics} dates={dates} date={date}
                     setDate={(d) => loadDay(d)} digest={digest} generate={generateDaily}
                     grantConsent={grantConsent} checkins={checkins} onCheck={onCheck}
                     seedDemo={seedDemo} collector={collector} refreshCollector={refreshCollector}
                     onData={() => boot(date)} />
            )}
          </div>
          {route === 'chat' && <Chat onGrantConsent={grantConsent} />}
          {route === 'plan' && (
            <Plan plan={plan} generate={generateWeekly} grantConsent={grantConsent}
                  checkins={checkins} onCheck={onCheck} />
          )}
          {route === 'checkin' && (
            <CheckIn digest={digest} plan={plan} checkins={checkins} onCheck={onCheck} />
          )}
          {route === 'privacy' && (
            <Privacy profile={profile} saveProfile={saveProfile} preview={preview}
                     refreshPreview={refreshPreview} eraseAll={eraseAll} />
          )}
          {route === 'prompts' && <Prompts />}
          {route === 'settings' && (
            <Settings settings={settings} saveSettings={saveSettings}
                      refresh={async () => setSettings(await api('/api/settings'))}
                      collector={collector} refreshCollector={refreshCollector}
                      onData={() => boot(date)} />
          )}
        </main>
      </div>
    </>
  );
}
