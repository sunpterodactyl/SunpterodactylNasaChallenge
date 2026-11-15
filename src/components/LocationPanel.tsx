import { useStore } from '../store'

export default function LocationPanel() {
  const results = useStore((s) => s.results)
  const selectedId = useStore((s) => s.selectedId)
  const setSelectedId = useStore((s) => s.setSelectedId)
  const starred = useStore((s) => s.starred)
  const toggleStar = useStore((s) => s.toggleStar)
  const notes = useStore((s) => s.notes)
  const setNote = useStore((s) => s.setNote)
  const searchError = useStore((s) => s.searchError)
  const searching = useStore((s) => s.searching)
  const catalog = useStore((s) => s.catalog)

  const selectedIndex = results.findIndex((m) => m.candidate.id === selectedId)
  const selected = selectedIndex >= 0 ? results[selectedIndex] : null
  const metricLabel = (id: string) => catalog?.metrics.find((m) => m.id === id)?.label ?? id

  return (
    <aside className="detail-rail" aria-label="Location details">
      <header className="rail-head">
        <h2>Location</h2>
        <span>{results.length ? `${results.length} matches` : 'No search yet'}</span>
      </header>

      {searching && <p className="status-msg">Searching…</p>}
      {!searching && searchError && (
        <p className="status-msg error" role="alert">
          {searchError}
        </p>
      )}

      {!searching && selected ? (
        <div className="location-card">
          <div className="location-title">
            <span className="rank">{selectedIndex + 1}</span>
            <div>
              <h3>{selected.candidate.name}</h3>
              <p>
                {selected.candidate.country} · {selected.candidate.category.replace('_', ' ')}
              </p>
            </div>
            <button
              type="button"
              className="star-btn"
              aria-pressed={starred.includes(selected.candidate.id)}
              aria-label={
                starred.includes(selected.candidate.id) ? 'Unstar location' : 'Star location'
              }
              onClick={() => toggleStar(selected.candidate.id)}
            >
              {starred.includes(selected.candidate.id) ? '★' : '☆'}
            </button>
          </div>

          <dl className="facts">
            <div>
              <dt>Score</dt>
              <dd>{(selected.score * 100).toFixed(0)}%</dd>
            </div>
            <div>
              <dt>Coverage</dt>
              <dd>{(selected.coverage * 100).toFixed(0)}%</dd>
            </div>
            <div>
              <dt>Evidence</dt>
              <dd>
                {selected.tier === 'direct'
                  ? '1st order'
                  : selected.tier === 'indirect'
                    ? '2nd order'
                    : '—'}
              </dd>
            </div>
            <div>
              <dt>Cost</dt>
              <dd>{selected.candidate.cost_index.toFixed(2)}</dd>
            </div>
            <div>
              <dt>Latitude</dt>
              <dd>{selected.candidate.lat.toFixed(2)}°</dd>
            </div>
            <div>
              <dt>Longitude</dt>
              <dd>{selected.candidate.lon.toFixed(2)}°</dd>
            </div>
          </dl>

          <h4>Metric match</h4>
          <div className="breakdown">
            {Object.entries(selected.breakdown).map(([id, val]) => (
              <div key={id}>
                <span>{metricLabel(id)}</span>
                <span className="bar" aria-hidden>
                  <i style={{ width: `${Math.round(val * 100)}%` }} />
                </span>
                <span>{(val * 100).toFixed(0)}%</span>
              </div>
            ))}
          </div>

          {starred.includes(selected.candidate.id) && (
            <textarea
              className="notes-field"
              placeholder="Notes for this analogue…"
              value={notes[selected.candidate.id] ?? ''}
              onChange={(e) => setNote(selected.candidate.id, e.target.value)}
              aria-label={`Notes for ${selected.candidate.name}`}
            />
          )}
        </div>
      ) : (
        !searching && (
          <p className="status-msg">
            Run a search, then choose a red marker to read the location.
          </p>
        )
      )}

      {results.length > 0 && (
        <ul className="rank-list">
          {results.map((m, i) => (
            <li key={m.candidate.id}>
              <button
                type="button"
                className={m.candidate.id === selectedId ? 'on' : ''}
                onClick={() => setSelectedId(m.candidate.id)}
              >
                <span className="rank">{i + 1}</span>
                <span className="result-name">{m.candidate.name}</span>
                <span className="stat">{(m.score * 100).toFixed(0)}%</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </aside>
  )
}
