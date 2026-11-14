import type { Catalog, Match, SearchRequest, Suggestion, Provider } from './types'

async function parseError(res: Response): Promise<string> {
  try {
    const body = await res.json()
    const detail = body?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) return detail.map((d) => d.msg ?? JSON.stringify(d)).join('; ')
    return res.statusText || `HTTP ${res.status}`
  } catch {
    return res.statusText || `HTTP ${res.status}`
  }
}

export async function fetchCatalog(): Promise<Catalog> {
  const res = await fetch('/api/catalog')
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function search(req: SearchRequest): Promise<Match[]> {
  const res = await fetch('/api/search', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(req),
  })
  if (!res.ok) throw new Error(await parseError(res))
  return res.json()
}

export async function suggest(prompt: string, provider: Provider): Promise<Suggestion> {
  const res = await fetch('/api/suggest', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ prompt, provider }),
  })
  if (!res.ok) {
    const msg = await parseError(res)
    if (/api.?key|authentication|OPENAI|ANTHROPIC/i.test(msg)) {
      const envVar = provider === 'openai' ? 'OPENAI_API_KEY' : 'ANTHROPIC_API_KEY'
      throw new Error(`Missing or invalid API key. Set ${envVar} on the server. (${msg})`)
    }
    throw new Error(msg)
  }
  return res.json()
}

export async function fetchTerrain(siteId: string): Promise<number[][]> {
  const res = await fetch(`/api/terrain/${encodeURIComponent(siteId)}`)
  if (!res.ok) throw new Error(await parseError(res))
  const data = await res.json()
  return data.grid
}
