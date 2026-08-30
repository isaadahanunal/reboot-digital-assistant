export function hm(minutes) {
  const m = Math.max(0, Math.round(minutes || 0));
  const h = Math.floor(m / 60);
  return h ? `${h}h ${String(m % 60).padStart(2, '0')}m` : `${m}m`;
}

export const CATEGORY_LABEL = {
  social: 'Social', entertainment: 'Video & music', communication: 'Messaging',
  work: 'Work & study', reading: 'Reading', games: 'Games', shopping: 'Shopping',
  utility: 'Utilities', other: 'Other',
};

export const DISCRETIONARY = ['social', 'entertainment', 'games', 'shopping'];

// Colour follows the entity, never its rank: a category keeps its slot even when
// the set of visible categories changes.
export const categoryColor = (cat) => `var(--cat-${cat in CATEGORY_LABEL ? cat : 'other'})`;

export const GOALS = [
  'Reduce doomscrolling',
  'Better sleep routine',
  'Deep work & study focus',
  'Mindful social media use',
  'Fewer pickups during work',
];

export const TRIGGERS = [
  'Late at night in bed',
  'First thing after waking up',
  'During study or work breaks',
  'When bored or procrastinating',
  'When stressed or overwhelmed',
];
