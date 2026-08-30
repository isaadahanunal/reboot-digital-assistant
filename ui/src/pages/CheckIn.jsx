import BarList from '../components/BarList.jsx';
import CheckRow from '../components/CheckRow.jsx';
import Icon from '../components/Icon.jsx';
import Note from '../components/Note.jsx';

const STATUS_COLOR = {
  done: 'var(--good)', partial: 'var(--warn)',
  skipped: 'var(--text-3)', too_hard: 'var(--alert)',
};
const STATUS_LABEL = { done: 'Did it', partial: 'Partly', skipped: 'Skipped', too_hard: 'Too hard' };

export default function CheckIn({ digest, plan, checkins, onCheck }) {
  const items = [];
  if (digest?.content?.micro_experiments) {
    digest.content.micro_experiments.forEach((e) =>
      items.push({ id: e.id, title: e.title, from: `Daily Digest · ${digest.date_key}`, date: digest.date_key }));
  }
  if (plan?.content?.days) {
    plan.content.days.forEach((d) =>
      items.push({ id: d.id, title: `${d.day} — ${d.focus}`, from: `7-Day Plan · ${plan.date_key}`, date: plan.date_key }));
  }
  const statusOf = (id) => checkins.find((k) => k.action_id === id)?.status;

  const counts = checkins.reduce((acc, c) => ({ ...acc, [c.status]: (acc[c.status] || 0) + 1 }), {});
  const totalCheckins = checkins.length;
  const doneCount = counts.done || 0;
  const completionPct = totalCheckins > 0 ? Math.round((doneCount / totalCheckins) * 100) : 0;

  const rows = Object.entries(counts).map(([k, v]) => ({
    label: STATUS_LABEL[k] || k, value: v, color: STATUS_COLOR[k] || 'var(--cat-other)',
  }));

  return (
    <div className="page stack">
      <div className="page-head">
        <div className="eyebrow">
          <Icon name="check" size={14} />
          <span>Adaptive Feedback Loop</span>
        </div>
        <h1>How did it go?</h1>
        <p>
          This feedback loop turns Reboot into a real coach. Your responses feed the next iteration,
          and the adaptation rules push towards <b>easier</b> habits when needed. A missed day is insight, not failure.
        </p>
      </div>

      {totalCheckins > 0 && (
        <div className="grid three">
          <div className="tile">
            <div className="k">Total Check-Ins</div>
            <div className="v">{totalCheckins}</div>
            <div className="f">Logged responses</div>
          </div>
          <div className="tile">
            <div className="k">Success Rate</div>
            <div className="v">{completionPct}%</div>
            <div className="f">{doneCount} marked as done</div>
          </div>
          <div className="tile">
            <div className="k">Active Tasks</div>
            <div className="v">{items.length}</div>
            <div className="f">Pending reflection</div>
          </div>
        </div>
      )}

      <div>
        <h3 style={{ marginBottom: 'var(--s-3)' }} className="row">
          <Icon name="target" size={18} />
          <span>Pending Reflections</span>
        </h3>
        {items.length === 0
          ? <Note tone="info" title="Nothing to check off yet">
              <p>Generate a daily digest or a 7-day plan first — your assigned micro-experiments will appear here automatically.</p>
            </Note>
          : items.map((i) => (
              <div className="action" key={`${i.date}-${i.id}`}>
                <div className="row" style={{ justifyContent: 'space-between' }}>
                  <div className="t">{i.title}</div>
                  <span className="badge flat">{i.from}</span>
                </div>
                <CheckRow actionId={i.id} dateKey={i.date} label={i.title}
                          status={statusOf(i.id)} onCheck={onCheck} />
              </div>
            ))}
      </div>

      <div className="card">
        <div className="row" style={{ gap: 'var(--s-2)', marginBottom: 'var(--s-2)' }}>
          <Icon name="activity" size={18} />
          <h3 style={{ margin: 0 }}>Check-In History</h3>
        </div>
        <p className="card-sub">Everything you have marked in the last two weeks.</p>
        <BarList rows={rows} empty="No check-ins recorded yet." />
      </div>
    </div>
  );
}
