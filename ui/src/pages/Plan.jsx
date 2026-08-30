import GenerateCard from '../components/GenerateCard.jsx';
import Icon from '../components/Icon.jsx';
import PlanView from '../components/PlanView.jsx';

export default function Plan({ plan, generate, grantConsent, checkins, onCheck }) {
  return (
    <div className="page stack">
      <div className="page-head">
        <div className="eyebrow">
          <Icon name="plan" size={14} />
          <span>7-Day Adaptive Strategy</span>
        </div>
        <h1>A plan you can actually finish</h1>
        <p>
          Observation first, one boundary in the middle, and one deliberately easy day — a plan with no
          easy day gets abandoned. Every action is anchored to your real usage patterns, with small fallback versions for difficult days.
        </p>
      </div>

      <GenerateCard
        label="Generate my 7-day plan"
        againLabel="Rebuild the plan from my latest check-ins"
        hint="Uses this week's measurements plus your check-in history, if you have any."
        onGenerate={generate}
        onGrantConsent={grantConsent}
        hasResult={Boolean(plan)}>
        {plan && (
          <div className="card">
            <PlanView envelope={plan} checkins={checkins} onCheck={onCheck} />
          </div>
        )}
      </GenerateCard>
    </div>
  );
}
