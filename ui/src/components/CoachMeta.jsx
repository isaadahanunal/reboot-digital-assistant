import Note from './Note.jsx';

const CONFIDENCE = {
  high:   ['good',  'Data confidence: high'],
  medium: ['warn',  'Data confidence: medium'],
  low:    ['alert', 'Data confidence: low'],
  none:   ['alert', 'No data'],
};

/* Provenance is shown, not implied: a reader can tell whether a model wrote this
   and how much the measurement behind it is worth.

   Guardrail activity is deliberately NOT shown here. It still runs, and every
   flag is stored with the artifact and returned by the API, but the badge fired
   often enough on good output that it stopped carrying information -- and a
   safety signal nobody believes is worse than no badge at all. */
export default function CoachMeta({ meta, provider, model }) {
  const [tone, label] = CONFIDENCE[meta.data_confidence] || CONFIDENCE.low;
  return (
    <div className="row" style={{ gap: 'var(--s-2)' }}>
      <span className={`badge ${tone}`}>{label}</span>
      {meta.ai_generated
        ? <span className="badge ai">AI-generated · {provider} / {model}</span>
        : <span className="badge flat">Rule-based · not AI-generated</span>}
      {meta.injection_suspected && <span className="badge alert">Context looked like an instruction</span>}
    </div>
  );
}

export function SupportCard({ card }) {
  return (
    <Note tone="alert" title={card.title} role="alert">
      <p>{card.body}</p>
      <ul style={{ paddingLeft: 18, margin: '0 0 var(--s-3)' }}>
        {card.resources.map((r) => (
          <li key={r.name}><b>{r.name}</b> ({r.region}) — {r.contact}</li>
        ))}
      </ul>
      <span className="hint">{card.note}</span>
    </Note>
  );
}
