/* Inline SVG only — no emoji as icons. Every icon is decorative here: it always
   sits next to a visible text label, so it is hidden from assistive tech. */
const PATHS = {
  today: 'M3 17l4-6 4 3 4-8 6 5M3 21h18',
  plan: 'M8 2v4M16 2v4M3 10h18M5 4h14a2 2 0 012 2v13a2 2 0 01-2 2H5a2 2 0 01-2-2V6a2 2 0 012-2z',
  check: 'M9 12l2 2 4-4M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  shield: 'M12 3l8 3v6c0 5-3.5 8.3-8 9-4.5-.7-8-4-8-9V6l8-3zM9 12l2 2 4-4',
  code: 'M8 6l-6 6 6 6M16 6l6 6-6 6',
  settings: 'M4 7h5M13 7h7M4 17h7M15 17h5M11 4v6M13 14v6',
  sun: 'M12 4V2M12 22v-2M4 12H2M22 12h-2M6.3 6.3L4.9 4.9M19.1 19.1l-1.4-1.4M6.3 17.7l-1.4 1.4M19.1 4.9l-1.4 1.4M16 12a4 4 0 11-8 0 4 4 0 018 0z',
  moon: 'M20 14.5A8.5 8.5 0 019.5 4a8.5 8.5 0 1010.5 10.5z',
  monitor: 'M3 5h18v11H3zM9 20h6M12 16v4',
  arrow: 'M5 12h14M13 6l6 6-6 6',
  back: 'M19 12H5M11 18l-6-6 6-6',
  alert: 'M12 8v5M12 17v0M10.3 3.9L2.4 17a2 2 0 001.7 3h15.8a2 2 0 001.7-3L13.7 3.9a2 2 0 00-3.4 0z',
  info: 'M12 16v-5M12 8v0M21 12a9 9 0 11-18 0 9 9 0 0118 0z',
  ok: 'M20 6L9 17l-5-5',
  copy: 'M9 9h10v10H9zM5 15H4a1 1 0 01-1-1V4a1 1 0 011-1h10a1 1 0 011 1v1',
  trash: 'M4 7h16M10 11v6M14 11v6M6 7l1 13h10l1-13M9 7V4h6v3',
  refresh: 'M3 12a9 9 0 0115-6.7L21 8M21 12a9 9 0 01-15 6.7L3 16M21 4v4h-4M3 20v-4h4',
  phone: 'M7 2h10a1 1 0 011 1v18a1 1 0 01-1 1H7a1 1 0 01-1-1V3a1 1 0 011-1zM11 19h2',
  laptop: 'M4 5h16v11H4zM2 20h20',
  sparkle: 'M12 3l1.9 5.1L19 10l-5.1 1.9L12 17l-1.9-5.1L5 10l5.1-1.9L12 3z',
  upload: 'M12 16V4M8 8l4-4 4 4M4 20h16',
  clock: 'M12 8v4l3 3M12 22a10 10 0 100-20 10 10 0 000 20z',
  trendingUp: 'M23 6l-9.5 9.5-5-5L1 18M17 6h6v6',
  trendingDown: 'M23 18l-9.5-9.5-5 5L1 6M17 18h6v-6',
  flame: 'M8.5 14.5A2.5 2.5 0 0011 12c0-1.38-.5-2-1-3-1.072-2.143-.224-4.054 2-6 .5 2.5 2 4.9 4 6.5 2 1.6 3 3.5 3 5.5a7 7 0 11-14 0c0-1.153.433-2.294 1-3a2.5 2.5 0 002.5 3z',
  target: 'M12 22a10 10 0 100-20 10 10 0 000 20zM12 18a6 6 0 100-12 6 6 0 000 12zM12 14a2 2 0 100-4 2 2 0 000 4z',
  zap: 'M13 2L3 14h9l-1 8 10-12h-9l1-8z',
  activity: 'M22 12h-4l-3 9L9 3l-3 9H2',
  eye: 'M1 12s4-8 11-8 11 8 11 8-4 8-11 8-11-8-11-8zM12 9a3 3 0 100 6 3 3 0 000-6z',
  compass: 'M12 22a10 10 0 100-20 10 10 0 000 20zM16.24 7.76l-2.12 6.36-6.36 2.12 2.12-6.36 6.36-2.12z',
  chevronRight: 'M9 18l6-6-6-6',
};

export default function Icon({ name, size = 20, className = '' }) {
  const d = PATHS[name] || PATHS.info;
  return (
    <svg className={className} width={size} height={size} viewBox="0 0 24 24" fill="none"
         stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"
         aria-hidden="true" focusable="false">
      <path d={d} />
    </svg>
  );
}
