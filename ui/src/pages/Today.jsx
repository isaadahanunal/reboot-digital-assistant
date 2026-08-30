import BarList from '../components/BarList.jsx';
import CollectorCard from '../components/CollectorCard.jsx';
import Digest from '../components/Digest.jsx';
import GenerateCard from '../components/GenerateCard.jsx';
import HourChart from '../components/HourChart.jsx';
import Icon from '../components/Icon.jsx';
import Note from '../components/Note.jsx';
import { CATEGORY_LABEL, DISCRETIONARY, categoryColor, hm } from '../format.js';

function Tile({ k, v, f, icon, delta, deltaPositiveGood }) {
  const isDeltaNum = typeof delta === 'number';
  const isGood = deltaPositiveGood ? delta > 0 : delta < 0;
  return (
    <div className="tile">
      <div className="k">
        {icon && <Icon name={icon} size={15} />}
        <span>{k}</span>
      </div>
      <div className="v">{v}</div>
      <div className="f row" style={{ gap: '6px', justifyContent: 'space-between', width: '100%' }}>
        <span>{f}</span>
        {isDeltaNum && (
          <span className={`badge ${isGood ? 'good' : 'warn'}`} style={{ fontSize: '11px', padding: '1px 6px' }}>
            <Icon name={delta > 0 ? 'trendingUp' : 'trendingDown'} size={12} />
            {delta > 0 ? `+${delta}%` : `${delta}%`}
          </span>
        )}
      </div>
    </div>
  );
}

export default function Today({ status, metrics, dates, date, setDate, digest, generate,
                               grantConsent, checkins, onCheck, seedDemo,
                               collector, refreshCollector, onData }) {
  if (!metrics) return <p className="hint">Loading your day…</p>;
  const m = metrics;
  const discretionary = Object.entries(m.by_category)
    .filter(([c]) => DISCRETIONARY.includes(c))
    .reduce((sum, [, v]) => sum + v, 0);
  const noData = (status?.data?.sessions ?? 0) === 0;

  return (
    <div className="page stack">
      <div className="page-head row" style={{ justifyContent: 'space-between', alignItems: 'flex-start' }}>
        <div className="grow">
          <div className="eyebrow">
            <Icon name="today" size={14} />
            <span>{date === status.today ? 'Live Daily Tracking' : 'Historical Day'}</span>
          </div>
          <h1>{date === status.today ? 'How today has gone so far' : date}</h1>
          <p>Real-time deterministic aggregation measured directly on your device.</p>
        </div>
        <div className="row" style={{ gap: 'var(--s-2)', background: 'var(--surface)', padding: '6px 10px', borderRadius: 'var(--r-md)', border: '1px solid var(--border)' }}>
          <Icon name="clock" size={16} />
          <label className="row" style={{ gap: 'var(--s-2)' }}>
            <span className="sr-only">Choose a day</span>
            <select
              value={date}
              onChange={(e) => setDate(e.target.value)}
              style={{ width: 'auto', border: 'none', background: 'transparent', padding: '4px 8px', fontWeight: 600, cursor: 'pointer' }}>
              {(dates.length ? dates : [status.today]).map((d) => (
                <option key={d} value={d}>{d === status.today ? `Today (${d})` : d}</option>
              ))}
            </select>
          </label>
        </div>
      </div>

      {noData && (
        <>
          <Note tone="info" title="No measurements yet">
            <p style={{ margin: '0 0 var(--s-3)' }}>
              Turn on recording below to measure this computer, or load a demo week to see the whole flow
              immediately.
            </p>
            <button type="button" className="btn quiet sm" onClick={seedDemo}>
              <Icon name="sparkle" size={16} />Load demo week
            </button>
          </Note>
          <CollectorCard state={collector} refresh={refreshCollector} onData={onData} compact />
        </>
      )}

      <div className="grid tiles">
        <Tile
          icon="clock"
          k="Total measured"
          v={hm(m.total_minutes)}
          f={m.days_of_history >= 3 ? 'vs 7-day average' : 'baseline forming'}
          delta={m.days_of_history >= 3 ? m.delta_vs_baseline_pct : undefined}
          deltaPositiveGood={false}
        />
        <Tile
          icon="flame"
          k="Discretionary"
          v={hm(discretionary)}
          f="social, video, gaming"
        />
        <Tile
          icon="moon"
          k="Late night 23–05"
          v={hm(m.late_night_minutes)}
          f={m.late_night_minutes ? 'affects morning energy' : 'clear tonight'}
        />
        <Tile
          icon="activity"
          k="Pickups"
          v={String(m.pickups)}
          f={`${m.switches} app switches`}
        />
        <Tile
          icon="target"
          k="Longest stretch"
          v={hm(m.longest_session_minutes)}
          f={m.longest_session_app || '—'}
        />
        <Tile
          icon="zap"
          k="Longest offline"
          v={hm(m.longest_offline_block_minutes)}
          f="deep rest block"
        />
      </div>

      <HourChart hourly={m.hourly_minutes} coverageHours={m.coverage_hours} />

      <div className="grid two">
        <div className="card">
          <h3>Where it went</h3>
          <p className="card-sub">Category totals, labelled directly.</p>
          <BarList rows={Object.entries(m.by_category).map(([cat, v]) => ({
            label: CATEGORY_LABEL[cat] || cat, value: v, color: categoryColor(cat),
          }))} />
        </div>
        <div className="card">
          <h3>Most-used</h3>
          <p className="card-sub">Top apps by foreground minutes.</p>
          <BarList rows={m.top_apps.map((a) => ({
            label: a.name, value: a.minutes, extra: `${a.opens}×`, color: categoryColor(a.category),
          }))} />
        </div>
      </div>

      <div>
        <h2 style={{ marginBottom: 'var(--s-3)' }}>Coach digest</h2>
        <GenerateCard
          label="Generate today's digest"
          againLabel="Regenerate this digest"
          hint="Generated only when you ask. The coach receives the aggregated numbers above — never a raw activity log."
          onGenerate={generate}
          onGrantConsent={grantConsent}
          hasResult={Boolean(digest)}>
          {digest && (
            <div className="card">
              <Digest envelope={digest} checkins={checkins} onCheck={onCheck} />
            </div>
          )}
        </GenerateCard>
      </div>
    </div>
  );
}
