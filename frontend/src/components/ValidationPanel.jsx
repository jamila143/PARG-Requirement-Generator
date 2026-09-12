export default function ValidationPanel({ validation }) {
  const passed = validation.status === 'Passed'
  const warned = validation.status === 'Passed with warnings'

  const pillClass = passed ? 'pill-good' : warned ? 'pill-warn' : 'pill-bad'

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="eyebrow">Step 5</span>
        <h2>Validation</h2>
      </div>

      <div className="validation-grid">
        <div className="validation-item">
          <span className="analysis-label">Status</span>
          <span className={`status-pill ${pillClass}`}>{validation.status}</span>
        </div>
        <div className="validation-item">
          <span className="analysis-label">Session process coverage</span>
          <span className="analysis-value">
            {validation.session_processes_covered} / {validation.session_total_processes} concepts
            ({validation.session_coverage_pct}%)
          </span>
        </div>
      </div>

      <div className="extraction-summary">
        <span className="analysis-label">Extraction summary</span>
        <div className="extraction-chips">
          <ExtractionChip label="Actor" ok={validation.extraction_summary.actor_found} />
          <ExtractionChip label="Action" ok={validation.extraction_summary.action_found} />
          <ExtractionChip label="Condition" ok={validation.extraction_summary.condition_found} />
          <ExtractionChip label="Outcome" ok={validation.extraction_summary.outcome_found} />
        </div>
      </div>

      {validation.issues.length > 0 && (
        <div className="issues-block">
          <span className="analysis-label">Issues found ({validation.issues.length})</span>
          <ul className="issues-list">
            {validation.issues.map((issue, i) => (
              <li key={i}>{issue}</li>
            ))}
          </ul>
        </div>
      )}

      <p className="scoring-note">
        Checks performed: {validation.checks_performed.join(', ')}.{' '}
        {validation.generic_fallback_count > 0 &&
          `${validation.generic_fallback_count} requirement(s) used generic fallback phrasing. `}
        {validation.note}
      </p>
    </section>
  )
}

function ExtractionChip({ label, ok }) {
  return <span className={`extraction-chip ${ok ? 'chip-ok' : 'chip-missing'}`}>{label}</span>
}

