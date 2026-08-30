import Icon from './Icon.jsx';

const NAV = [
  ['today', 'Today', 'today'],
  ['chat', 'Chat', 'sparkle'],
  ['plan', 'Plan', 'plan'],
  ['checkin', 'Check-in', 'check'],
  ['privacy', 'Privacy', 'shield'],
];

function ThemeControl({ theme, setTheme }) {
  const modes = [['light', 'sun', 'Light'], ['system', 'monitor', 'System'], ['dark', 'moon', 'Dark']];
  return (
    <div className="theme" role="group" aria-label="Colour theme">
      {modes.map(([value, icon, label]) => (
        <button key={value} type="button" aria-pressed={theme === value} title={label}
                onClick={() => setTheme(value)}>
          <Icon name={icon} size={15} />
          <span className="sr-only">{label}</span>
        </button>
      ))}
    </div>
  );
}

export default function Sidebar({ route, theme, setTheme }) {
  return (
    <nav className="sidebar" aria-label="Main navigation">
      <div className="brand">
        <span className="mark" aria-hidden="true">R</span>
        <div>
          <b>Reboot</b>
          <span>Digital Coach</span>
        </div>
      </div>

      <div className="nav">
        {NAV.map(([id, label, icon]) => (
          <a key={id} href={`#${id}`} aria-current={route === id ? 'page' : undefined}>
            <Icon name={icon} size={18} />
            <span>{label}</span>
          </a>
        ))}
        <a href="#settings" aria-current={route === 'settings' ? 'page' : undefined} className="settings-link">
          <Icon name="settings" size={18} />
          <span>Settings</span>
        </a>
      </div>

      <div className="side-foot">
        <ThemeControl theme={theme} setTheme={setTheme} />
      </div>
    </nav>
  );
}
