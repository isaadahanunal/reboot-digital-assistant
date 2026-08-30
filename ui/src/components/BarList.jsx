import { hm } from '../format.js';

export default function BarList({ rows, empty = 'Nothing recorded.' }) {
  if (!rows.length) return <p className="hint" style={{ padding: 'var(--s-3) 0' }}>{empty}</p>;
  const total = rows.reduce((sum, r) => sum + r.value, 0);
  const max = Math.max(1, ...rows.map((r) => r.value));

  return (
    <ul className="barlist">
      {rows.map((r) => {
        const pctOfTotal = total > 0 ? Math.round((r.value / total) * 100) : 0;
        const pctOfMax = Math.max(3, Math.round((r.value / max) * 100));
        return (
          <li key={r.label}>
            <span className="n">
              <span className="chip" style={{ background: r.color, boxShadow: `0 0 8px ${r.color}66` }} />
              <span>{r.label}</span>
              {pctOfTotal > 0 && (
                <span className="badge flat" style={{ fontSize: '11px', padding: '1px 6px', fontWeight: 600 }}>
                  {pctOfTotal}%
                </span>
              )}
            </span>
            <span className="v">
              {hm(r.value)}
              {r.extra && <span className="hint" style={{ fontWeight: 500 }}> · {r.extra}</span>}
            </span>
            <span className="track">
              <span
                className="fill"
                style={{
                  width: `${pctOfMax}%`,
                  background: `linear-gradient(90deg, ${r.color}, ${r.color}dd)`,
                  boxShadow: `0 0 8px ${r.color}33`,
                }}
              />
            </span>
          </li>
        );
      })}
    </ul>
  );
}
