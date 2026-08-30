import { useEffect, useState } from 'react';
import Icon from './Icon.jsx';

/* Destructive confirmation without a modal: the button becomes its own two-step
   confirm and reverts on its own after a few seconds. A browser confirm() dialog
   is a popup the user cannot style, cannot read on mobile, and cannot escape from
   with a keyboard on some platforms. */
export default function ConfirmButton({ children, confirmLabel, onConfirm, icon = 'trash', timeout = 5000 }) {
  const [armed, setArmed] = useState(false);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!armed) return undefined;
    const t = setTimeout(() => setArmed(false), timeout);
    return () => clearTimeout(t);
  }, [armed, timeout]);

  if (!armed) {
    return (
      <button type="button" className="btn danger" onClick={() => setArmed(true)}>
        <Icon name={icon} size={18} />{children}
      </button>
    );
  }
  return (
    <div className="btnrow" role="group" aria-label="Confirm this action">
      <button type="button" className="btn danger" disabled={busy}
              onClick={async () => { setBusy(true); try { await onConfirm(); } finally { setBusy(false); setArmed(false); } }}>
        {busy ? <span className="spin" /> : <Icon name={icon} size={18} />}
        {confirmLabel}
      </button>
      <button type="button" className="btn quiet" onClick={() => setArmed(false)}>Cancel</button>
    </div>
  );
}
