const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000'

export async function checkHealth() {
  const res = await fetch(`${API_URL}/health`)
  if (!res.ok) throw new Error('Health check failed')
  return res.json()
}

export async function generateRequirements(userStory) {
  const res = await fetch(`${API_URL}/generate`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ user_story: userStory }),
  })

  if (!res.ok) {
    let detail = 'The server returned an error.'
    try {
      const body = await res.json()
      detail = body.detail || detail
    } catch (e) {
      // response wasn't JSON; keep default message
    }
    throw new Error(detail)
  }

  return res.json()
}

export async function fetchHistoryList(limit = 50, offset = 0) {
  const res = await fetch(`${API_URL}/history?limit=${limit}&offset=${offset}`)
  if (!res.ok) throw new Error('Could not load history.')
  return res.json()
}

export async function fetchHistoryDetail(id) {
  const res = await fetch(`${API_URL}/history/${id}`)
  if (!res.ok) throw new Error('Could not load that history entry.')
  return res.json()
}

export async function deleteHistoryEntry(id) {
  const res = await fetch(`${API_URL}/history/${id}`, { method: 'DELETE' })
  if (!res.ok) throw new Error('Could not delete that history entry.')
  return res.json()
}

