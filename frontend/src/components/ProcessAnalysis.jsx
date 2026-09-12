export default function ProcessAnalysis({ result }) {
  const { process_concept, ontology_mapping, domain_entity, ner, scoring } = result

  return (
    <section className="panel">
      <div className="panel-head">
        <span className="eyebrow">Step 2</span>
        <h2>Process analysis</h2>
      </div>

      <div className="analysis-grid">
        <div className="analysis-item">
          <span className="analysis-label">Detected process concept</span>
          <span className="analysis-value mono">
            {process_concept}
            {scoring.low_confidence && <span className="inline-flag" title="Below confidence threshold">tentative</span>}
          </span>
        </div>
        <div className="analysis-item">
          <span className="analysis-label">Ontology mapping</span>
          <span className="analysis-value mono">{ontology_mapping.replaceAll('->', '→')}</span>
        </div>
        {domain_entity && (
          <div className="analysis-item">
            <span className="analysis-label">Domain entity (object of the requirements)</span>
            <span className="analysis-value mono">{domain_entity}</span>
          </div>
        )}
      </div>

      <div className="ner-grid">
        <NerField label="Actor" field={ner.actor} />
        <NerField label="Action" field={ner.action} />
        <ClauseField label="Condition" field={ner.condition} />
        <ClauseField label="Outcome" field={ner.outcome} />
      </div>
    </section>
  )
}

function NerField({ label, field }) {
  const empty = !field.text
  return (
    <div className={`ner-field ${field.low_confidence ? 'ner-field-warn' : ''}`}>
      <div className="ner-field-head">
        <span className="ner-label">{label}</span>
        {!empty && (
          <span className="ner-conf mono" title="Model confidence for this span">
            {(field.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <span className={`ner-value ${empty ? 'ner-empty' : ''}`}>
        {field.text || 'not extracted'}
      </span>
      {field.low_confidence && <span className="ner-warn-note">low confidence — excluded from generated text</span>}
    </div>
  )
}

const DECISION_LABEL = {
  accepted: 'accepted',
  flagged: 'flagged — excluded',
  rejected: 'rejected',
  not_found: 'not extracted',
}

/**
 * Condition/Outcome went through boundary detection + candidate scoring
 * (see backend pipeline.py), so they show a decision status and, when
 * relevant, a small badge indicating the linguistic layer corrected the
 * span or found a connector word anchoring the clause.
 */
function ClauseField({ label, field }) {
  const empty = field.decision === 'not_found' || field.decision === 'rejected'
  const cardClass =
    field.decision === 'flagged' ? 'ner-field-warn' : field.decision === 'accepted' ? 'ner-field-ok' : ''

  return (
    <div className={`ner-field ${cardClass}`}>
      <div className="ner-field-head">
        <span className="ner-label">{label}</span>
        {!empty && (
          <span className="ner-conf mono" title="Candidate score (BIO confidence + connector + grammar + verbatim)">
            {(field.confidence * 100).toFixed(0)}%
          </span>
        )}
      </div>
      <span className={`ner-value ${empty ? 'ner-empty' : ''}`}>
        {field.text || 'not extracted'}
      </span>
      <div className="ner-badges">
        <span className={`decision-badge decision-${field.decision}`}>{DECISION_LABEL[field.decision]}</span>
        {field.connector_detected && <span className="mini-badge">connector found</span>}
        {field.boundary_corrected && <span className="mini-badge">boundary corrected</span>}
      </div>
    </div>
  )
}
