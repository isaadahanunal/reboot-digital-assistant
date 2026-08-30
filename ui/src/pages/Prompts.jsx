import { useEffect, useState } from 'react';
import { api } from '../api.js';
import Icon from '../components/Icon.jsx';
import Note from '../components/Note.jsx';

export default function Prompts() {
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    api('/api/prompts').then(setData).catch(setError);
  }, []);

  return (
    <div className="page stack">
      <div className="page-head">
        <div className="eyebrow">
          <Icon name="code" size={14} />
          <span>Prompt Engineering Lab</span>
        </div>
        <h1>System Prompts &amp; Techniques</h1>
        <p>
          Served live from <code>GET /api/prompts</code>. Complete transparency into instructions,
          safety guardrails, chain-of-thought steps, and output schema definitions.
        </p>
      </div>

      {error && <Note tone="alert" title="Could not load the prompts">{error.message}</Note>}
      {!data && !error && <p className="hint">Loading prompt repository…</p>}

      {data?.prompts.map((p) => (
        <details className="prompt" key={p.id}>
          <summary>
            <div className="row" style={{ gap: 'var(--s-2)', width: '100%', justifyContent: 'space-between' }}>
              <span>{p.name}</span>
              <span className="badge flat" style={{ fontSize: '11px' }}>{p.techniques.length} techniques</span>
            </div>
          </summary>
          <div className="body">
            <div className="tags">{p.techniques.map((t) => <span key={t}>{t}</span>)}</div>
            <p style={{ color: 'var(--text-2)', marginBottom: 'var(--s-3)' }}><b>Rationale &amp; Design: </b>{p.rationale}</p>
            <pre className="json">{p.text}</pre>
          </div>
        </details>
      ))}

      {data && (
        <details className="prompt">
          <summary>Output schemas (structured output)</summary>
          <div className="body">
            <p style={{ color: 'var(--text-2)' }}>
              Both calls are schema-constrained at the API level, so "the model returned prose instead of
              JSON" is impossible rather than merely handled — and it forces the model to fill the humble
              fields it would otherwise skip, like <code>confidence</code> and <code>data_i_could_not_see</code>.
            </p>
            <pre className="json">{JSON.stringify(data.schemas, null, 2)}</pre>
          </div>
        </details>
      )}
    </div>
  );
}
