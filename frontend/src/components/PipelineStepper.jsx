const STAGES = [
  'Preprocessing',
  'Process Classification',
  'Ontology Mapping',
  'Requirement Generation',
  'Validation',
]

/**
 * A quiet, content-grounded "signature" element: PARG's own five-phase
 * pipeline (see the notebook / thesis), shown as a horizontal progress
 * stepper. Idle before a request, animates through stages while loading,
 * and lands on "done" once a result exists.
 */
export default function PipelineStepper({ status }) {
  // status: 'idle' | 'running' | 'done'
  return (
    <div className={`stepper stepper-${status}`} aria-hidden="true">
      {STAGES.map((stage, i) => (
        <div className="stepper-item" key={stage}>
          <div className="stepper-dot">{i + 1}</div>
          <div className="stepper-label">{stage}</div>
          {i < STAGES.length - 1 && <div className="stepper-line" />}
        </div>
      ))}
    </div>
  )
}
