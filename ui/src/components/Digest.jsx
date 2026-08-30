import CheckRow from './CheckRow.jsx';
import CoachMeta, { SupportCard } from './CoachMeta.jsx';
import Icon from './Icon.jsx';
import Note from './Note.jsx';

export default function Digest({ envelope, checkins, onCheck }) {
  if (envelope.kind === 'support_card') return <SupportCard card={envelope.content} />;
  const c = envelope.content;
  const statusOf = (id) => checkins.find((k) => k.action_id === id)?.status;

  return (
    <div className="stack">
      <CoachMeta meta={envelope.meta} provider={envelope.provider} model={envelope.model} />
      
      <div style={{ paddingBottom: 'var(--s-3)', borderBottom: '1px solid var(--border)' }}>
        <h2 className="headline">{c.headline}</h2>
        <p className="lede">{c.summary}</p>
      </div>

      <div>
        <h3 style={{ marginBottom: 'var(--s-3)' }} className="row">
          <Icon name="activity" size={18} />
          <span>Key Observations</span>
        </h3>
        <div className="grid two">
          {c.observations?.map((o) => (
            <div className="obs" key={o.metric} style={{ marginTop: 0 }}>
              <div className="k">{o.metric}</div>
              <div className="v">{o.value}</div>
              <div className="r">{o.reading}</div>
            </div>
          ))}
        </div>
      </div>

      <Note tone="good" title="What went well">
        <p>{c.what_went_well}</p>
      </Note>

      <div className="quote">
        <div className="row" style={{ gap: '6px', marginBottom: '4px' }}>
          <Icon name="compass" size={16} />
          <b style={{ color: 'var(--text)' }}>Pattern Hypothesis (A guess, not a finding):</b>
        </div>
        <span>{c.pattern_hypothesis}</span>
      </div>

      <div>
        <h3 style={{ marginBottom: 'var(--s-3)' }} className="row">
          <Icon name="target" size={18} />
          <span>Micro-Experiments for Tomorrow</span>
        </h3>
        {c.micro_experiments?.map((e) => (
          <div className="action" key={e.id}>
            <div className="row" style={{ justifyContent: 'space-between' }}>
              <span className="t grow">{e.title}</span>
              <span className="badge ai row" style={{ gap: '4px' }}>
                <Icon name="clock" size={13} />
                <span>{e.effort_minutes} min setup</span>
              </span>
            </div>
            <div className="ifthen">
              <Icon name="zap" size={16} />
              <span><b>If-Then Rule: </b>{e.if_then}</span>
            </div>
            <p className="why" style={{ margin: 0 }}><b>Why this works: </b>{e.why_this}</p>
            <CheckRow actionId={e.id} dateKey={envelope.date_key} label={e.title}
                      status={statusOf(e.id)} onCheck={onCheck} />
          </div>
        ))}
      </div>

      <div className="card" style={{ background: 'var(--surface-2)', border: '1px solid var(--accent-border)' }}>
        <div className="row" style={{ gap: 'var(--s-2)', color: 'var(--accent)', marginBottom: 'var(--s-2)' }}>
          <Icon name="shield" size={18} />
          <h3 style={{ margin: 0, color: 'inherit' }}>Boundary Worth Setting</h3>
        </div>
        <p style={{ margin: 'var(--s-2) 0', fontWeight: 700, fontSize: '15px' }}>{c.boundary_suggestion.rule}</p>
        <p className="hint" style={{ margin: 0 }}><b>How to configure: </b>{c.boundary_suggestion.how_to_set_it}</p>
      </div>

      <div className="ask">
        <div className="row" style={{ gap: '8px', alignItems: 'flex-start' }}>
          <Icon name="info" size={20} />
          <div>
            <b style={{ display: 'block', marginBottom: '4px' }}>Question for you:</b>
            <span>{c.user_check_question}</span>
          </div>
        </div>
      </div>

      <p className="hint row" style={{ margin: 0, gap: '6px', alignItems: 'center' }}>
        <Icon name="eye" size={15} />
        <span><b>What this model cannot see: </b>{c.data_i_could_not_see}</span>
      </p>

      <p className="legal">{envelope.meta.disclaimer}</p>
    </div>
  );
}
