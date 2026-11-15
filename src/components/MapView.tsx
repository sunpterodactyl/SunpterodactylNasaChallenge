import { useEffect, useMemo, useRef } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'
import { useStore } from '../store'

function resultPin(rank: number, selected: boolean) {
  const fill = selected ? '#9a241c' : '#d23b32'
  const ring = selected ? '#fff4e8' : '#ffffff'
  return L.divIcon({
    className: 'pin-wrap',
    html: `<svg class="pin${selected ? ' selected' : ''}" viewBox="0 0 32 44" width="32" height="44" aria-hidden="true">
      <path d="M16 42s12-13.2 12-24A12 12 0 1 0 4 18c0 10.8 12 24 12 24z" fill="${fill}" stroke="${ring}" stroke-width="1.6"/>
      <circle cx="16" cy="17" r="7.2" fill="#fff"/>
      <text x="16" y="20.2" text-anchor="middle" font-size="9" font-family="Instrument Sans, sans-serif" font-weight="700" fill="${fill}">${rank}</text>
    </svg>`,
    iconSize: [32, 44],
    iconAnchor: [16, 42],
    popupAnchor: [0, -38],
  })
}

function targetPin() {
  return L.divIcon({
    className: 'pin-wrap',
    html: `<svg class="pin target" viewBox="0 0 32 44" width="32" height="44" aria-hidden="true">
      <path d="M16 42s12-13.2 12-24A12 12 0 1 0 4 18c0 10.8 12 24 12 24z" fill="#3d7f90" stroke="#e9ebe7" stroke-width="1.6"/>
      <circle cx="16" cy="17" r="6" fill="#e9ebe7"/>
    </svg>`,
    iconSize: [32, 44],
    iconAnchor: [16, 42],
    popupAnchor: [0, -38],
  })
}

function FitBounds({
  points,
}: {
  points: Array<{ lat: number; lon: number }>
}) {
  const map = useMap()
  useEffect(() => {
    if (points.length === 0) return
    const bounds = L.latLngBounds(points.map((p) => [p.lat, p.lon] as [number, number]))
    map.fitBounds(bounds.pad(0.3), { animate: false })
  }, [map, points])
  return null
}

function FocusSelected({
  point,
  signature,
}: {
  point: { lat: number; lon: number } | null
  signature: string
}) {
  const map = useMap()
  const lastSignature = useRef(signature)
  useEffect(() => {
    if (lastSignature.current !== signature) {
      lastSignature.current = signature
      return
    }
    if (!point) return
    const reduce = window.matchMedia('(prefers-reduced-motion: reduce)').matches
    map.panTo([point.lat, point.lon], { animate: !reduce })
  }, [map, point, signature])
  return null
}

function normalizeLon(lon: number) {
  // Marius Hills uses -303.3 in mock data; Leaflet expects [-180, 180]
  let x = lon
  while (x > 180) x -= 360
  while (x < -180) x += 360
  return x
}

export default function MapView() {
  const catalog = useStore((s) => s.catalog)
  const targetId = useStore((s) => s.targetId)
  const results = useStore((s) => s.results)
  const selectedId = useStore((s) => s.selectedId)
  const setSelectedId = useStore((s) => s.setSelectedId)

  const target = catalog?.targets.find((t) => t.id === targetId)

  const points = useMemo(() => {
    const list: Array<{ lat: number; lon: number }> = []
    for (const m of results) {
      list.push({ lat: m.candidate.lat, lon: normalizeLon(m.candidate.lon) })
    }
    return list
  }, [results])

  const selectedPoint = useMemo(() => {
    const hit = results.find((m) => m.candidate.id === selectedId)
    if (!hit) return null
    return { lat: hit.candidate.lat, lon: normalizeLon(hit.candidate.lon) }
  }, [results, selectedId])

  return (
    <div className="map-root" role="region" aria-label="Analogue map">
      <MapContainer
        center={[20, 0]}
        zoom={2}
        style={{ height: '100%', width: '100%' }}
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <FitBounds points={points} />
        <FocusSelected
          point={selectedPoint}
          signature={points.map((p) => `${p.lat},${p.lon}`).join('|')}
        />

        {target && (
          <Marker
            position={[target.lat, normalizeLon(target.lon)]}
            icon={targetPin()}
            zIndexOffset={100}
          >
            <Popup>
              <strong>{target.name}</strong>
              <br />
              {target.body === 'moon' ? 'Moon' : 'Mars'} reference site
            </Popup>
          </Marker>
        )}

        {results.map((m, i) => (
          <Marker
            key={m.candidate.id}
            position={[m.candidate.lat, normalizeLon(m.candidate.lon)]}
            icon={resultPin(i + 1, m.candidate.id === selectedId)}
            zIndexOffset={m.candidate.id === selectedId ? 500 : i}
            eventHandlers={{
              click: () => setSelectedId(m.candidate.id),
            }}
          >
            <Popup>
              <strong>
                #{i + 1} {m.candidate.name}
              </strong>
              <br />
              Score {m.score.toFixed(3)} · coverage {m.coverage.toFixed(2)}
            </Popup>
          </Marker>
        ))}
      </MapContainer>
    </div>
  )
}
