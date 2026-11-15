import { useEffect, useMemo, useState } from 'react'
import { CircleMarker, MapContainer, Popup, TileLayer, Tooltip, useMap } from 'react-leaflet'
import 'leaflet/dist/leaflet.css'

interface Region {
  region: string
  lat: number
  lon: number
  kind: string
  status: 'kept' | 'dropped'
  patches: number
  airport: string | null
  airport_km: number | null
  field_months: number | null
  cost_tier: number | null
  permit: boolean | null
  source: string | null
}

interface Patch {
  id: string
  region: string
  lat: number
  lon: number
}

interface ExplorePatch {
  id: string
  lat: number
  lon: number
  label: string
}

interface Locations {
  regions: Region[]
  patches: Patch[]
  explore?: ExplorePatch[]
}

const CARTO_KEY = import.meta.env.VITE_CARTO_KEY
const TILES = CARTO_KEY
  ? { url: `https://basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}.png?key=${CARTO_KEY}`, subdomains: undefined }
  : { url: 'https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', subdomains: 'abcd' }

export const KIND_COLOUR: Record<string, string> = {
  arid: '#b87a1e',
  dune: '#d9a441',
  volcanic: '#8b3a2f',
  polar: '#5f97a8',
  flat: '#6f8a4f',
  mountain: '#4b4f78',
}

const label = (s: string) => s.replace(/_/g, ' ')

function FlyTo({ to }: { to: { lat: number; lon: number; zoom: number } | null }) {
  const map = useMap()
  useEffect(() => {
    if (!to) return
    const reduce = window.matchMedia?.('(prefers-reduced-motion: reduce)').matches
    if (reduce) map.setView([to.lat, to.lon], to.zoom)
    else map.flyTo([to.lat, to.lon], to.zoom, { duration: 0.8 })
  }, [map, to])
  return null
}

export default function MapPage() {
  const [data, setData] = useState<Locations | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [focus, setFocus] = useState<{ lat: number; lon: number; zoom: number } | null>(null)
  const [active, setActive] = useState<string | null>(null)
  const [showExplore, setShowExplore] = useState(true)

  useEffect(() => {
    fetch('/locations.json')
      .then((r) => {
        if (!r.ok) throw new Error(`Could not load locations (${r.status})`)
        return r.json()
      })
      .then(setData)
      .catch((e: Error) => setError(e.message))
  }, [])

  const kindOf = useMemo(() => Object.fromEntries((data?.regions ?? []).map((r) => [r.region, r.kind])), [data])
  const kinds = useMemo(() => [...new Set((data?.regions ?? []).map((r) => r.kind))].sort(), [data])

  if (error) return <div className="map-page"><p className="empty-note" role="alert">{error}</p></div>
  if (!data) return <div className="map-page"><p className="empty-note">Loading locations…</p></div>

  const kept = data.regions.filter((r) => r.status === 'kept')

  return (
    <div className="map-page">
      <aside className="map-side">
        <h2>Earth corpus</h2>
        <p className="muted small">
          {kept.length} regions searched · {data.patches.length} patches (32 × 32 km each).{' '}
          {data.regions.length - kept.length} seed regions were dropped in QC because most patches fell in the sea.
        </p>
        <ul className="legend" aria-label="Landform kinds">
          {kinds.map((k) => (
            <li key={k}>
              <span className="dot" style={{ background: KIND_COLOUR[k] ?? '#777' }} aria-hidden />
              {k}
            </li>
          ))}
          <li>
            <span className="dot dropped" aria-hidden />
            dropped
          </li>
        </ul>
        {!!data.explore?.length && (
          <label className="layer-toggle">
            <input type="checkbox" checked={showExplore} onChange={(e) => setShowExplore(e.target.checked)} />
            <span className="dot explore" aria-hidden />
            {data.explore.length} new candidate patches (Discover)
          </label>
        )}
        <ol className="region-list">
          {data.regions.map((r) => (
            <li key={r.region}>
              <button
                className={`region-btn ${active === r.region ? 'selected' : ''} ${r.status}`}
                onClick={() => {
                  setActive(r.region)
                  setFocus({ lat: r.lat, lon: r.lon, zoom: 8 })
                }}
              >
                <span className="dot" style={{ background: r.status === 'kept' ? KIND_COLOUR[r.kind] : undefined }} aria-hidden />
                <span className="region-name">{label(r.region)}</span>
                <span className="muted num">{r.status === 'kept' ? `${r.patches} patches` : 'dropped'}</span>
              </button>
            </li>
          ))}
        </ol>
        <button className="link reset" onClick={() => { setActive(null); setFocus({ lat: 15, lon: 0, zoom: 2 }) }}>
          Show whole world
        </button>
      </aside>

      <div className="map-wrap">
        <MapContainer center={[15, 0]} zoom={2} minZoom={2} worldCopyJump className="map" aria-label="Map of Earth analogue regions">
          <TileLayer
            url={TILES.url}
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors &copy; <a href="https://carto.com/attributions">CARTO</a>'
            {...(TILES.subdomains ? { subdomains: TILES.subdomains } : {})}
            maxZoom={12}
          />
          {showExplore && (data.explore ?? []).map((p) => (
            <CircleMarker key={p.id} center={[p.lat, p.lon]} radius={2.5}
              pathOptions={{ color: '#6b777c', weight: 1, fillColor: '#ffffff', fillOpacity: 0.9 }}>
              <Tooltip>{p.id} · new candidate · {p.label}</Tooltip>
            </CircleMarker>
          ))}
          <FlyTo to={focus} />
          {data.patches.map((p) => (
            <CircleMarker key={p.id} center={[p.lat, p.lon]} radius={3}
              pathOptions={{ color: KIND_COLOUR[kindOf[p.region]] ?? '#777', weight: 1, fillOpacity: 0.55 }}>
              <Tooltip>{p.id} · {p.lat.toFixed(3)}, {p.lon.toFixed(3)}</Tooltip>
            </CircleMarker>
          ))}
          {data.regions.map((r) => (
            <CircleMarker key={r.region} center={[r.lat, r.lon]} radius={active === r.region ? 10 : 7}
              eventHandlers={{ click: () => setActive(r.region) }}
              pathOptions={r.status === 'kept'
                ? { color: '#1d2a2e', weight: active === r.region ? 3 : 1.5, fillColor: KIND_COLOUR[r.kind], fillOpacity: 0.9 }
                : { color: '#5d6a6e', weight: 1.5, dashArray: '3 3', fillColor: '#f5f6f2', fillOpacity: 0.9 }}>
              <Popup>
                <div className="popup">
                  <b>{label(r.region)}</b> <span className="muted">· {r.kind}</span>
                  <div className="num">{r.lat.toFixed(2)}, {r.lon.toFixed(2)}</div>
                  {r.status === 'kept' ? (
                    <>
                      <div>{r.patches} patches searched</div>
                      <div>Nearest airport: {r.airport} · <span className="num">{r.airport_km?.toFixed(0)} km</span></div>
                      <div>Cost tier: {r.cost_tier ?? 'not curated'} · Season: {r.field_months == null ? 'not curated' : `${r.field_months} mo`}</div>
                      {r.source && <div className="muted">Source: {r.source}</div>}
                    </>
                  ) : (
                    <div className="muted">Dropped in QC: fewer than 15 patches on land.</div>
                  )}
                </div>
              </Popup>
            </CircleMarker>
          ))}
        </MapContainer>
      </div>
    </div>
  )
}
