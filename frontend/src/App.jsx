import { useEffect, useState } from 'react'
import InputPanel from './components/InputPanel.jsx'
import PipelineStepper from './components/PipelineStepper.jsx'
import ProcessAnalysis from './components/ProcessAnalysis.jsx'
import ScoringPanel from './components/ScoringPanel.jsx'
import RequirementsList from './components/RequirementsList.jsx'
import ValidationPanel from './components/ValidationPanel.jsx'
import HistoryPanel from './components/HistoryPanel.jsx'
import { checkHealth, generateRequirements } from './api.js'

export default function App() {
  const [tab, setTab] = useState('generate') // 'generate' | 'history'
  const [story, setStory] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState(null)
  const [warning, setWarning] = useState(null)
  const [result, setResult] = useState(null)
  const [viewingHistory, setViewingHistory] = useState(false)
  const [backend, setBackend] = useState({ checked: false, ready: false, detail: '' })
  const [copied, setCopied] = useState(false)

  useEffect(() => {
    checkHealth()
      .then((h) => {
        setBackend({
          checked: true,
          ready: h.status === 'ready',
          detail:
            h.status === 'ready'
              ? `${h.num_process_concepts} process concepts loaded on ${h.device}`
              : 'Models or dataset not loaded yet — see backend terminal output.',
        })
      })
      .catch(() => {
        setBackend({ checked: true, ready: false, detail: 'Cannot reach the backend at all.' })
      })
  }, [])

  async function handleGenerate() {
    setWarning(null)
    setError(null)

    if (!story.trim()) {
      setWarning('Please enter a user story before generating requirements.')
      return
    }

    setLoading(true)
    setResult(null)
    setViewingHistory(false)
    try {
      const data = await generateRequirements(story)
      setResult(data)
    } catch (e) {
      setError(e.message || 'Something went wrong while generating requirements.')
    } finally {
      setLoading(false)
    }
  }

  function handleClear() {
    setStory('')
    setResult(null)
    setError(null)
    setWarning(null)
    setViewingHistory(false)
  }

  function handleViewHistoryEntry(entry) {
    setStory(entry.user_story)
    setResult(entry)
    setViewingHistory(true)
    setTab('generate')
    setError(null)
    setWarning(null)
  }

  function handleCopy() {
    if (!result) return
    const text = result.requirements.map((r, i) => `${i + 1}. ${r.text}`).join('\n')
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true)
      setTimeout(() => setCopied(false), 1800)
    })
  }

  function handleDownload() {
    if (!result) return
    const text = [
      `PARG Generated Requirements`,
      `User story: ${result.user_story}`,
      `Process concept: ${result.process_concept}`,
      `Ontology mapping: ${result.ontology_mapping}`,
      '',
      ...result.requirements.map((r, i) => `${i + 1}. ${r.text}`),
    ].join('\n')
    const blob = new Blob([text], { type: 'text/plain' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'parg-requirements.txt'
    a.click()
    URL.revokeObjectURL(url)
  }

  const pipelineStatus = loading ? 'running' : result ? 'done' : 'idle'

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <span className="brand-mark">PARG</span>
          <div className="brand-text">
            <h1>Process-Aware Requirement Generation</h1>
            <p>Turn one user story into structured, ontology-grounded software requirements.</p>
          </div>
        </div>
        {backend.checked && (
          <div className={`backend-badge ${backend.ready ? 'backend-ok' : 'backend-down'}`}>
            <span className="backend-dot" />
            {backend.ready ? 'Backend ready' : 'Backend not ready'}
            <span className="backend-detail">{backend.detail}</span>
          </div>
        )}
      </header>

      <main className="app-main">
        <div className="tab-row">
          <button
            className={`tab-btn ${tab === 'generate' ? 'tab-btn-active' : ''}`}
            onClick={() => setTab('generate')}
          >
            Generate
          </button>
          <button
            className={`tab-btn ${tab === 'history' ? 'tab-btn-active' : ''}`}
            onClick={() => setTab('history')}
          >
            History
          </button>
        </div>

        {tab === 'history' && <HistoryPanel onViewEntry={handleViewHistoryEntry} />}

        {tab === 'generate' && (
          <>
            <PipelineStepper status={pipelineStatus} />

            <InputPanel
              value={story}
              onChange={setStory}
              onGenerate={handleGenerate}
              onClear={handleClear}
              loading={loading}
              disabled={backend.checked && !backend.ready}
            />

            {warning && <div className="banner banner-warn">{warning}</div>}
            {error && <div className="banner banner-error">{error}</div>}
            {backend.checked && !backend.ready && (
              <div className="banner banner-warn">
                The backend says it isn't ready ({backend.detail}). Generate will not work until
                the model and dataset files are in place — see the README.
              </div>
            )}

            {loading && (
              <div className="loading-block">
                <div className="spinner" />
                <span>Running the PARG pipeline…</span>
              </div>
            )}

            {result && !loading && (
              <>
                {viewingHistory && (
                  <div className="banner banner-info">
                    Viewing a saved result from history ({new Date(result.created_at).toLocaleString()}).
                  </div>
                )}
                {!viewingHistory && result.history_id && (
                  <div className="banner banner-info">Saved to history (#{result.history_id}).</div>
                )}
                {result.warnings.length > 0 && (
                  <div className="banner banner-warn">
                    <strong>Review before trusting this result:</strong>
                    <ul className="warning-list">
                      {result.warnings.map((w, i) => (
                        <li key={i}>{w}</li>
                      ))}
                    </ul>
                  </div>
                )}
                <ProcessAnalysis result={result} />
                <ScoringPanel scoring={result.scoring} />
                <RequirementsList
                  requirements={result.requirements}
                  onCopy={handleCopy}
                  onDownload={handleDownload}
                />
                <ValidationPanel validation={result.validation} />
                {copied && <div className="toast">Copied to clipboard</div>}
              </>
            )}
          </>
        )}
      </main>

      <footer className="app-footer">
        <span>PARG research demonstration — not a general-purpose chat assistant.</span>
      </footer>
    </div>
  )
}
