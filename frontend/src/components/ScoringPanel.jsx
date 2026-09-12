export default function ScoringPanel({ scoring }) {
  const pct = (x) => `${Math.round(x * 100)}%`

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="eyebrow">Algorithm A1</span>
        <h2>Hybrid scoring</h2>
      </div>

      <div className="score-bars">
        <ScoreBar label="Model confidence" value={scoring.model_confidence} />
        <ScoreBar label="Ontology similarity" value={scoring.ontology_similarity} />
        <ScoreBar label="Hybrid score" value={scoring.hybrid_score} emphasized />
      </div>

      <div className="score-footer">
        <span className="mono small">
          Hybrid = {scoring.alpha} × confidence + {scoring.beta} × similarity
        </span>
        <span className={`status-pill ${scoring.selection_status.startsWith('High') ? 'pill-good' : 'pill-warn'}`}>
          {scoring.selection_status}
        </span>
      </div>
      <p className="scoring-note">
        The hybrid score is reported as a confidence indicator alongside the model's own
        prediction — it does not override which process concept was selected. See the README
        for why.
      </p>
    </section>
  )
}

function ScoreBar({ label, value, emphasized }) {
  const pct = Math.round(value * 100)
  return (
    <div className="score-row">
      <div className="score-row-head">
        <span>{label}</span>
        <span className="mono">{value.toFixed(3)}</span>
      </div>
      <div className="score-track">
        <div
          className={`score-fill ${emphasized ? 'score-fill-emph' : ''}`}
          style={{ width: `${pct}%` }}
        />
      </div>
    </div>
  )
}
