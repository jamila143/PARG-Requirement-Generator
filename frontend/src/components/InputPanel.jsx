export default function InputPanel({ value, onChange, onGenerate, onClear, loading, disabled }) {
  return (
    <section className="panel input-panel">
      <div className="panel-head">
        <span className="eyebrow">Step 1</span>
        <h2>Enter a user story</h2>
      </div>
      <p className="panel-hint">
        Write one agile user story. PARG will identify the process it describes and generate
        structured, IEEE&nbsp;830-format requirements from it.
      </p>
      <textarea
        className="story-input"
        placeholder="As a bank customer, I want to transfer money online so that I can pay my bills conveniently."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={5}
        disabled={loading}
      />
      <div className="input-actions">
        <button
          className="btn btn-primary"
          onClick={onGenerate}
          disabled={loading || disabled}
        >
          {loading ? 'Generating…' : 'Generate Requirements'}
        </button>
        <button className="btn btn-ghost" onClick={onClear} disabled={loading}>
          Clear
        </button>
      </div>
    </section>
  )
}
