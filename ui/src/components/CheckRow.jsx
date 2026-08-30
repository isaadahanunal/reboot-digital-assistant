import Icon from './Icon.jsx';

const OPTIONS = [
  ['done', 'Did it', 'ok', 'var(--good)'],
  ['partial', 'Partly', 'zap', 'var(--warn)'],
  ['skipped', 'Skipped', 'arrow', 'var(--text-3)'],
  ['too_hard', 'Too hard', 'alert', 'var(--alert)'],
];

export default function CheckRow({ actionId, dateKey, status, onCheck, label }) {
  return (
    <div className="checkrow" role="group" aria-label={`How did "${label}" go?`}>
      {OPTIONS.map(([value, text, icon, color]) => {
        const isSelected = status === value;
        return (
          <button
            key={value}
            type="button"
            aria-pressed={isSelected}
            onClick={() => onCheck(dateKey, actionId, value)}
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: '5px',
              borderColor: isSelected ? color : undefined,
              color: isSelected ? 'var(--on-accent)' : undefined,
              background: isSelected ? color : undefined,
            }}>
            <Icon name={icon} size={14} />
            <span>{text}</span>
          </button>
        );
      })}
    </div>
  );
}
