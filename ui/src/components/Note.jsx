import Icon from './Icon.jsx';

const ICON = { info: 'info', good: 'ok', warn: 'alert', alert: 'alert' };

/* Status is never colour-alone: every note carries an icon and, where it matters,
   a bold lead-in naming the state. */
export default function Note({ tone = 'info', title, children, role }) {
  return (
    <div className={`note ${tone}`} role={role || (tone === 'alert' ? 'alert' : undefined)}>
      <Icon name={ICON[tone]} size={18} />
      <div>
        {title && <b>{title}</b>}
        {children}
      </div>
    </div>
  );
}
