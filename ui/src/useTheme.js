import { useCallback, useEffect, useState } from 'react';

const KEY = 'reboot-theme';

/* Three explicit states rather than a two-way toggle: "system" has to be
   reachable, otherwise a user who picks dark once can never hand the decision
   back to their OS. */
export function useTheme() {
  const [theme, setThemeState] = useState(() => {
    try { return localStorage.getItem(KEY) || 'light'; } catch { return 'light'; }
  });

  useEffect(() => {
    const root = document.documentElement;
    if (theme === 'system') {
      root.removeAttribute('data-theme');
    } else {
      root.setAttribute('data-theme', theme);
    }
    try { localStorage.setItem(KEY, theme); } catch { /* private mode */ }
  }, [theme]);

  const setTheme = useCallback((next) => setThemeState(next), []);
  return [theme, setTheme];
}
