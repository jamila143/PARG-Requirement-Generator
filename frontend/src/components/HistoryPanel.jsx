import { useEffect, useState } from 'react'
import { fetchHistoryList, fetchHistoryDetail, deleteHistoryEntry } from '../api.js'

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export default function HistoryPanel({ onViewEntry }) {
  const [items, setItems] = useState([])
  const [total, setTotal] = useState(0)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState(null)

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await fetchHistoryList(50, 0)
      setItems(data.items)
      setTotal(data.total)
    } catch (e) {
      setError(e.message)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
  }, [])

  async function handleView(id) {
    try {
      const detail = await fetchHistoryDetail(id)
      onViewEntry(detail)
    } catch (e) {
      setError(e.message)
    }
  }

  async function handleDelete(id, e) {
    e.stopPropagation()
    if (!confirm('Delete this saved story and its requirements? This cannot be undone.')) return
    try {
      await deleteHistoryEntry(id)
      load()
    } catch (e2) {
      setError(e2.message)
    }
  }

  return (
    <section className="panel">
      <div className="panel-head panel-head-row">
        <div>
          <span className="eyebrow">History</span>
          <h2>Saved stories ({total})</h2>
        </div>
        <div className="req-actions">
          <a className="btn btn-ghost btn-small" href={`${API_URL}/history/export/xlsx`}>
            Download as Excel
          </a>
          <a className="btn btn-ghost btn-small" href={`${API_URL}/history/export/db`}>
            Download database file
          </a>
          <button className="btn btn-ghost btn-small" onClick={load}>
            Refresh
          </button>
        </div>
      </div>

      {loading && <p className="panel-hint">Loading…</p>}
      {error && <div className="banner banner-error">{error}</div>}

      {!loading && items.length === 0 && !error && (
        <p className="panel-hint">
          Nothing saved yet. Every story you generate requirements for is saved here automatically.
        </p>
      )}

      <ul className="history-list">
        {items.map((item) => (
          <li key={item.id} className="history-item" onClick={() => handleView(item.id)}>
            <div className="history-item-main">
              <span className="history-story">{item.user_story}</span>
              <div className="history-meta">
                <span className="mono small">{item.process_concept}</span>
                <span className="mono small">hybrid {item.hybrid_score.toFixed(3)}</span>
                <span className={`status-pill ${item.validation_status === 'Passed' ? 'pill-good' : 'pill-warn'}`}>
                  {item.validation_status}
                </span>
                <span className="history-date">{new Date(item.created_at).toLocaleString()}</span>
              </div>
            </div>
            <button className="btn btn-ghost btn-small" onClick={(e) => handleDelete(item.id, e)}>
              Delete
            </button>
          </li>
        ))}
      </ul>
    </section>
  )
}
