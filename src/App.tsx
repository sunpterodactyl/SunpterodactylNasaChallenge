import { useCallback, useEffect, useState } from 'react'
import { fetchCatalog, runSearch } from './api'
import BriefForm from './components/BriefForm'
import MapPage from './components/MapPage'
import Results from './components/Results'
import Sessions from './components/Sessions'
import TerrainPair from './components/TerrainPair'
import { loadSessions, storeSessions } from './sessions'
import type { Brief, Catalog, SearchResult, Session } from './types'

const DEFAULT_BRIEF: Omit<Brief, 'target_id'> = {
  objective: 'mobility',
  stage: 'early',
  mode: 'shape_magnitude',
  max_cost_tier: 4,
  max_airport_km: 1000,
  min_field_months: 0,
  k: 10,
}

type View = 'search' | 'map'
const viewFromHash = (): View => (window.location.hash === '#/map' ? 'map' : 'search')

export default function App() {
  const [view, setView] = useState<View>(viewFromHash)
  const [catalog, setCatalog] = useState<Catalog | null>(null)
  const [brief, setBrief] = useState<Brief | null>(null)
  const [result, setResult] = useState<SearchResult | null>(null)
  const [selected, setSelected] = useState(0)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [exaggeration, setExaggeration] = useState(5)
  const [sessions, setSessions] = useState<Session[]>(() => loadSessions())
  const [starred, setStarred] = useState<string[]>([])
  const [notes, setNotes] = useState('')

  useEffect(() => {
    const onHash = () => setView(viewFromHash())
    window.addEventListener('hashchange', onHash)
    return () => window.removeEventListener('hashchange', onHash)
  }, [])

  useEffect(() => {
    fetchCatalog()
      .then((c) => {
        setCatalog(c)
        setBrief({ ...DEFAULT_BRIEF, target_id: c.targets[0]?.id ?? '' })
      })
      .catch((e: Error) => setError(e.message))
  }, [])

  const search = useCallback(async (b: Brief) => {
    setLoading(true)
    setError(null)
    try {
      const r = await runSearch(b)
      setResult(r)
      setSelected(0)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  const persist = (next: Session[]) => {
    setSessions(next)
    if (!storeSessions(next)) setError('Could not save sessions in this browser (storage unavailable).')
  }

  const target = catalog?.targets.find((t) => t.id === (result?.target_id ?? brief?.target_id)) ?? null
  const match = result?.matches[selected] ?? null

  return (
    <div className="app">
      <header className="topbar">
        <h1>Terrain Mapper</h1>
        <p>Earth terrain patches ranked by 3D shape similarity to Moon targets</p>
        <nav className="tabs" aria-label="Pages">
          <a href="#/" aria-current={view === 'search' ? 'page' : undefined}>Search</a>
          <a href="#/map" aria-current={view === 'map' ? 'page' : undefined}>Map</a>
        </nav>
      </header>

      {error && (
        <div className="error" role="alert">
          <span>{error}</span>
          <button className="icon" aria-label="Dismiss error" onClick={() => setError(null)}>
            ×
          </button>
        </div>
      )}

      {view === 'map' ? <MapPage /> : (
      <main className="layout">
        <aside className="sidebar">
          {catalog && brief ? (
            <BriefForm catalog={catalog} brief={brief} loading={loading} onChange={setBrief} onRun={() => search(brief)} />
          ) : (
            <p className="empty-note">{error ? 'Catalog unavailable.' : 'Loading catalog…'}</p>
          )}
          {brief && (
            <Sessions
              sessions={sessions}
              notes={notes}
              starredCount={starred.length}
              onNotes={setNotes}
              onSave={(name) =>
                persist([
                  { name, brief, starred, notes, saved_at: new Date().toISOString() },
                  ...sessions.filter((s) => s.name !== name),
                ])
              }
              onLoad={(s) => {
                setBrief(s.brief)
                setStarred(s.starred)
                setNotes(s.notes)
                search(s.brief)
              }}
              onDelete={(name) => persist(sessions.filter((s) => s.name !== name))}
            />
          )}
        </aside>

        <TerrainPair
          target={target}
          match={match ? { label: `${match.region.replace(/_/g, ' ')} (${match.patch_id})`, grid: match.grid } : null}
          exaggeration={exaggeration}
          onExaggeration={setExaggeration}
        />

        <Results
          result={result}
          selected={selected}
          starred={starred}
          onSelect={setSelected}
          onStar={(id) => setStarred((s) => (s.includes(id) ? s.filter((x) => x !== id) : [...s, id]))}
        />
      </main>
      )}
    </div>
  )
}
