import CheckRow from './CheckRow.jsx';
import CoachMeta, { SupportCard } from './CoachMeta.jsx';
import Icon from './Icon.jsx';
import Note from './Note.jsx';

export default function PlanView({ envelope, checkins, onCheck }) {
  if (envelope.kind === 'support_card') return <SupportCard card={envelope.content} />;
  const c = envelope.content;
  const statusOf = (id) => checkins.find((k) => k.action_id === id)?.status;

  return (
    <div className="stack">
      <CoachMeta meta={envelope.meta} provider={envelope.provider} model={envelope.model} />
      <div style={{ paddingBottom: 'var(--s-3)', borderBottom: '1px solid var(--border)' }}>
        <h2 className="headline">{c.plan_title}</h2>
        <p className="lede">{c.north_star}</p>
      </div>

      <div className="card" style={{ background: 'var(--surface-2)', border: '1px solid var(--accent-border)' }}>
        <div className="eyebrow" style={{ marginBottom: 'var(--s-2)' }}>
          <Icon name="target" size={14} />
          <span>Weekly Target</span>
        </div>
        <div style={{ fontSize: '20px', fontWeight: 800, margin: 'var(--s-1) 0', color: 'var(--accent)' }}>
          {c.weekly_target.metric}: <span style={{ textDecoration: 'line-through', opacity: 0.6 }}>{c.weekly_target.from_value}</span> → <b>{c.weekly_target.to_value}</b>
        </div>
        <p className="hint" style={{ margin: 0 }}>{c.weekly_target.rationale}</p>
      </div>

      <div>
        <h3 style={{ marginBottom: 'var(--s-3)' }} className="row">
          <Icon name="calendar" size={18} />
          <span>7-Day Action Roadmap</span>
        </h3>
        {c.days?.map((d) => (
          <div className="day" key={d.id}>
            <div className="row" style={{ justifyContent: 'space-between', alignItems: 'center' }}>
              <span className="daynum">{d.day}</span>
              <b className="grow" style={{ fontSize: '15px' }}>{d.focus}</b>
              <span className="badge ai row" style={{ gap: '4px' }}>
                <Icon name="clock" size={13} />
                <span>{d.effort_minutes} min</span>
              </span>
            </div>
            <p style={{ margin: 'var(--s-3) 0 0', color: 'var(--text-2)', fontSize: '14px' }}>{d.action}</p>
            <div className="ifthen">
              <Icon name="zap" size={15} />
              <span><b>If-Then: </b>{d.if_then}</span>
            </div>
            <div className="fallback">
              <b>Bad day fallback: </b>{d.fallback}
            </div>
            <CheckRow actionId={d.id} dateKey={envelope.date_key} label={`${d.day} — ${d.focus}`}
                      status={statusOf(d.id)} onCheck={onCheck} />
          </div>
        ))}
      </div>

      <div className="grid two">
        <div className="card">
          <div className="row" style={{ gap: 'var(--s-2)', marginBottom: 'var(--s-3)' }}>
            <Icon name="laptop" size={18} />
            <h3 style={{ margin: 0 }}>Environment Changes</h3>
          </div>
          <ul style={{ paddingLeft: 18, color: 'var(--text-2)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {c.environment_changes?.map((e) => <li key={e}>{e}</li>)}
          </ul>
        </div>
        <div className="card">
          <div className="row" style={{ gap: 'var(--s-2)', marginBottom: 'var(--s-3)' }}>
            <Icon name="shield" size={18} />
            <h3 style={{ margin: 0 }}>Guardrails</h3>
          </div>
          <ul style={{ paddingLeft: 18, color: 'var(--text-2)', display: 'flex', flexDirection: 'column', gap: '6px' }}>
            {c.guardrails?.map((g) => <li key={g}>{g}</li>)}
          </ul>
        </div>
      </div>

      <Note tone="info" title="What changed and why">
        <p>{c.adaptation_note}</p>
      </Note>
      
      <div className="ask">
        <div className="row" style={{ gap: '8px', alignItems: 'flex-start' }}>
          <Icon name="info" size={20} />
          <div>
            <b style={{ display: 'block', marginBottom: '4px' }}>Review Question:</b>
            <span>{c.review_question}</span>
          </div>
        </div>
      </div>
      <p className="legal">{envelope.meta.disclaimer}</p>
    </div>
  );
}
