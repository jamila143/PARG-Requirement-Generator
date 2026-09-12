export default function RequirementsList({ requirements, onCopy, onDownload }) {
  return (
    <section className="panel">
      <div className="panel-head panel-head-row">
        <div>
          <span className="eyebrow">Step 4</span>
          <h2>Generated requirements</h2>
        </div>
        <div className="req-actions">
          <button className="btn btn-ghost btn-small" onClick={onCopy}>
            Copy requirements
          </button>
          <button className="btn btn-ghost btn-small" onClick={onDownload}>
            Download .txt
          </button>
        </div>
      </div>

      <ol className="requirement-list">
        {requirements.map((r, i) => (
          <li className={`requirement-card ${r.requires_review ? 'requirement-card-warn' : ''}`} key={i}>
            <div className="requirement-number">{i + 1}</div>
            <div className="requirement-body">
              <div className="requirement-step-row">
                <span className="requirement-step">{r.step}</span>
                {r.step_purpose && <span className="requirement-purpose">{r.step_purpose}</span>}
                {r.repaired && <span className="mini-badge mini-badge-ok">auto-repaired</span>}
                {r.requires_review && <span className="mini-badge mini-badge-warn">needs review</span>}
              </div>
              <p className="requirement-text">{r.text}</p>
              {r.requires_review && r.unrepaired_issues.length > 0 && (
                <p className="requirement-issue-note">{r.unrepaired_issues.join('; ')}</p>
              )}
            </div>
          </li>
        ))}
      </ol>
    </section>
  )
}
