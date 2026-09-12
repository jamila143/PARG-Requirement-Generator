import { useEffect, useRef, useState } from 'react'
import HistoryPanel from './components/HistoryPanel.jsx'
import { checkHealth, generateRequirements } from './api.js'

export default function App() {
  const [tab, setTab] = useState('chat') // 'chat' | 'history'
  const [messages, setMessages] = useState([]) // [{id, story, status, result, error}]
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [backend, setBackend] = useState({ checked: false, ready: false, detail: '' })
  const scrollRef = useRef(null)

  useEffect(() => {
    checkHealth()
      .then((h) => {
        setBackend({
          checked: true,
          ready: h.status === 'ready',
          detail:
            h.status === 'ready'
              ? `${h.num_process_concepts} process concepts loaded on ${h.device}`
              : h.error || 'Models or dataset not loaded yet.',
        })
      })
      .catch(() => setBackend({ checked: true, ready: false, detail: 'Cannot reach the backend.' }))
  }, [])

  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' })
  }, [messages, sending])

  async function handleSend() {
    const story = input.trim()
    if (!story || sending) return

    const id = Date.now()
    setMessages((prev) => [...prev, { id, story, status: 'loading', result: null, error: null }])
    setInput('')
    setSending(true)

    try {
      const result = await generateRequirements(story)
      setMessages((prev) => prev.map((m) => (m.id === id ? { ...m, status: 'done', result } : m)))
    } catch (e) {
      setMessages((prev) =>
        prev.map((m) => (m.id === id ? { ...m, status: 'error', error: e.message || 'Something went wrong.' } : m))
      )
    } finally {
      setSending(false)
    }
  }

  function handleKeyDown(e) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  function handleViewHistoryEntry(entry) {
    const id = Date.now()
    setMessages((prev) => [...prev, { id, story: entry.user_story, status: 'done', result: entry, error: null }])
    setTab('chat')
  }

  return (
    <div className="app-shell">
      <header className="app-header">
        <div className="app-header-inner">
          <span className="brand-mark">PARG</span>
          <div className="brand-text">
            <h1>Process-Aware Requirement Generation</h1>
            <p>Ask for requirements, story by story — keep going as long as you like.</p>
          </div>
        </div>
        {backend.checked && (
          <div className={`backend-badge ${backend.ready ? 'backend-ok' : 'backend-down'}`}>
            <span className="backend-dot" />
            {backend.ready ? 'Backend ready' : 'Backend not ready'}
            <span className="backend-detail">{backend.detail}</span>
          </div>
        )}
        <div className="tab-row tab-row-header">
          <button className={`tab-btn ${tab === 'chat' ? 'tab-btn-active' : ''}`} onClick={() => setTab('chat')}>
            Chat
          </button>
          <button className={`tab-btn ${tab === 'history' ? 'tab-btn-active' : ''}`} onClick={() => setTab('history')}>
            History
          </button>
        </div>
      </header>

      {tab === 'history' && (
        <main className="app-main">
          <HistoryPanel onViewEntry={handleViewHistoryEntry} />
        </main>
      )}

      {tab === 'chat' && (
        <div className="chat-shell">
          <div className="chat-scroll" ref={scrollRef}>
            {messages.length === 0 && (
              <div className="chat-empty">
                <p>Type a user story below and press Enter.</p>
                <p className="chat-empty-example">
                  e.g. "As a bank customer, I want to transfer money online so that I can pay my bills conveniently."
                </p>
              </div>
            )}
            {messages.map((m) => (
              <ChatTurn key={m.id} message={m} />
            ))}
            {backend.checked && !backend.ready && (
              <div className="banner banner-warn chat-banner">
                Backend isn't ready ({backend.detail}). Requests will fail until the model/dataset files are in place.
              </div>
            )}
          </div>

          <div className="chat-input-bar">
            <textarea
              className="chat-input"
              placeholder="Enter a user story…"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              rows={2}
              disabled={sending}
            />
            <button className="btn btn-primary chat-send-btn" onClick={handleSend} disabled={sending || !input.trim()}>
              {sending ? '…' : 'Send'}
            </button>
          </div>
        </div>
      )}
    </div>
  )
}

function ChatTurn({ message }) {
  const { story, status, result, error } = message

  function handleCopy() {
    if (!result) return
    const text = result.requirements.map((r, i) => `${i + 1}. ${r.text}`).join('\n')
    navigator.clipboard.writeText(text)
  }

  return (
    <div className="chat-turn">
      <div className="chat-bubble chat-bubble-user">{story}</div>

      <div className="chat-bubble chat-bubble-assistant">
        {status === 'loading' && (
          <div className="chat-loading">
            <div className="spinner" />
            <span>Generating…</span>
          </div>
        )}

        {status === 'error' && <div className="chat-error">{error}</div>}

        {status === 'done' && result && (
          <>
            <ol className="chat-req-list">
              {result.requirements.map((r, i) => (
                <li key={i}>
                  {r.text}
                </li>
              ))}
            </ol>
            <button className="chat-copy-btn" onClick={handleCopy}>
              Copy
            </button>
          </>
        )}
      </div>
    </div>
  )
}
