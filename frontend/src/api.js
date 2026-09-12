// When the frontend is served BY the same backend (as it is once deployed --
// see Section 12 of the README), the API lives at the same origin as the
// page itself, so an empty string ("" -> relative URLs like "/generate")
// is the right default. VITE_API_URL still overrides this for local
// development, where the frontend (5173) and backend (8000) are separate.
const API_URL = import.meta.env.VITE_API_URL || ''

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

