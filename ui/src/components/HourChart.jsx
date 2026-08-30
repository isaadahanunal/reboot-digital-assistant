import { useState } from 'react';
import Icon from './Icon.jsx';
import { hm } from '../format.js';

const LATE_BANDS = [[0, 5], [23, 1]];   // 00:00-05:00 and 23:00-24:00

export default function HourChart({ hourly, coverageHours }) {
  const [tip, setTip] = useState(null);
  const max = Math.max(1, ...hourly);
  const peakHour = hourly.indexOf(max);

  return (
    <div className="card">
      <div className="row" style={{ marginBottom: 'var(--s-4)', justifyContent: 'space-between' }}>
        <div>
          <div className="row" style={{ gap: 'var(--s-2)' }}>
            <Icon name="activity" size={18} />
            <h3>When the screen time happened</h3>
          </div>
          <div className="hint">Minutes per hour of the 24h day</div>
        </div>
        <div className="row" style={{ gap: 'var(--s-2)' }}>
          {max > 0 && (
            <span className="badge flat">
              Peak: {String(peakHour).padStart(2, '0')}:00 ({hm(max)})
            </span>
          )}
          <span className="badge ai">
            {coverageHours ? `Observed ${coverageHours}h span` : 'No data'}
          </span>
        </div>
      </div>

      <div className="chart-plot">
        {LATE_BANDS.map(([start, span]) => (
          <div key={start} className="chart-band" aria-hidden="true"
               style={{ left: `${(start / 24) * 100}%`, width: `${(span / 24) * 100}%` }} />
        ))}
        {hourly.map((v, h) => (
          <div key={h} className="chart-col" tabIndex={0} role="img"
               aria-label={`${String(h).padStart(2, '0')}:00, ${hm(v)}`}
               onMouseEnter={(e) => setTip({ h, v, rect: e.currentTarget.getBoundingClientRect() })}
               onFocus={(e) => setTip({ h, v, rect: e.currentTarget.getBoundingClientRect() })}
               onMouseLeave={() => setTip(null)}
               onBlur={() => setTip(null)}>
            {v > 0 && (
              <div
                className="chart-bar"
                style={{
                  height: `${Math.max(4, (v / max) * 100)}%`,
                  background: (h < 5 || h >= 23)
                    ? 'linear-gradient(180deg, #f59e0b 0%, #d97706 100%)'
                    : undefined,
                }}
              />
            )}
          </div>
        ))}
        <div className="chart-base" aria-hidden="true" />
      </div>

      <div className="chart-axis" aria-hidden="true">
        {hourly.map((_, h) => (
          <span key={h} style={{ color: h % 6 === 0 ? 'var(--text)' : 'var(--text-3)' }}>
            {h % 6 === 0 ? `${String(h).padStart(2, '0')}:00` : (h % 3 === 0 ? '·' : '')}
          </span>
        ))}
      </div>

      <div className="row" style={{ margin: 'var(--s-3) 0 0', justifyContent: 'space-between', alignItems: 'center' }}>
        <p className="hint row" style={{ margin: 0, gap: '6px', alignItems: 'center' }}>
          <Icon name="moon" size={14} />
          <span>Shaded zone is <b>23:00–05:00</b>, the late-night window tied to sleep quality.</span>
        </p>
      </div>

      {tip && (
        <div className="tooltip on" role="status"
             style={{ left: Math.min(window.innerWidth - 170, Math.max(10, tip.rect.left - 20)), top: Math.max(8, tip.rect.top - 48) }}>
          <div className="row" style={{ gap: '6px' }}>
            {(tip.h < 5 || tip.h >= 23) && <Icon name="moon" size={14} />}
            <span>{String(tip.h).padStart(2, '0')}:00 – {String((tip.h + 1) % 24).padStart(2, '0')}:00</span>
          </div>
          <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--accent)' }}>{hm(tip.v)}</div>
        </div>
      )}
    </div>
  );
}
