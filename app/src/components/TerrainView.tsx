import { useEffect, useMemo, useState } from 'react'
import { Canvas } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import * as THREE from 'three'
import { fetchTerrain } from '../api'
import { useStore } from '../store'

function heightColor(h: number, min: number, max: number): THREE.Color {
  const t = max === min ? 0.5 : (h - min) / (max - min)
  // paper → glacier → basalt
  const low = new THREE.Color('#c9d0c4')
  const mid = new THREE.Color('#8fb8c4')
  const high = new THREE.Color('#3a4750')
  if (t < 0.5) return low.clone().lerp(mid, t * 2)
  return mid.clone().lerp(high, (t - 0.5) * 2)
}

function TerrainMesh({
  grid,
  exaggeration,
}: {
  grid: number[][]
  exaggeration: number
}) {
  const geometry = useMemo(() => {
    const n = grid.length
    const geo = new THREE.PlaneGeometry(10, 10, n - 1, n - 1)
    const pos = geo.attributes.position as THREE.BufferAttribute
    const colors: number[] = []
    let min = Infinity
    let max = -Infinity
    for (let y = 0; y < n; y++) {
      for (let x = 0; x < n; x++) {
        const h = grid[y][x]
        if (h < min) min = h
        if (h > max) max = h
      }
    }
    for (let i = 0; i < pos.count; i++) {
      const row = Math.floor(i / n)
      const col = i % n
      const h = grid[row][col]
      pos.setZ(i, h * exaggeration * 0.02)
      const c = heightColor(h, min, max)
      colors.push(c.r, c.g, c.b)
    }
    geo.setAttribute('color', new THREE.Float32BufferAttribute(colors, 3))
    geo.computeVertexNormals()
    return geo
  }, [grid, exaggeration])

  return (
    <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]}>
      <meshStandardMaterial vertexColors flatShading side={THREE.DoubleSide} />
    </mesh>
  )
}

function TerrainScene({
  grid,
  exaggeration,
  sunAzimuth,
  sunElevation,
}: {
  grid: number[][] | null
  exaggeration: number
  sunAzimuth: number
  sunElevation: number
}) {
  const lightPos = useMemo(() => {
    const az = (sunAzimuth * Math.PI) / 180
    const el = (sunElevation * Math.PI) / 180
    const r = 12
    return [
      r * Math.cos(el) * Math.sin(az),
      r * Math.sin(el),
      r * Math.cos(el) * Math.cos(az),
    ] as [number, number, number]
  }, [sunAzimuth, sunElevation])

  if (!grid) {
    return (
      <mesh>
        <boxGeometry args={[0.01, 0.01, 0.01]} />
        <meshBasicMaterial color="#888" />
      </mesh>
    )
  }

  return (
    <>
      <ambientLight intensity={0.35} />
      <directionalLight position={lightPos} intensity={1.15} />
      <TerrainMesh grid={grid} exaggeration={exaggeration} />
      <OrbitControls enableDamping={false} />
    </>
  )
}

export default function TerrainView() {
  const catalog = useStore((s) => s.catalog)
  const targetId = useStore((s) => s.targetId)
  const results = useStore((s) => s.results)
  const selectedId = useStore((s) => s.selectedId)

  const [exaggeration, setExaggeration] = useState(1.5)
  const [sunAzimuth, setSunAzimuth] = useState(45)
  const [sunElevation, setSunElevation] = useState(35)
  const [targetGrid, setTargetGrid] = useState<number[][] | null>(null)
  const [resultGrid, setResultGrid] = useState<number[][] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)

  const target = catalog?.targets.find((t) => t.id === targetId)
  const selected = results.find((m) => m.candidate.id === selectedId)

  useEffect(() => {
    let cancelled = false
    async function load() {
      if (!targetId) return
      setLoading(true)
      setError(null)
      try {
        const tg = await fetchTerrain(targetId)
        if (cancelled) return
        setTargetGrid(tg)
        if (selectedId) {
          const rg = await fetchTerrain(selectedId)
          if (cancelled) return
          setResultGrid(rg)
        } else {
          setResultGrid(null)
        }
      } catch (e) {
        if (!cancelled) setError(e instanceof Error ? e.message : String(e))
      } finally {
        if (!cancelled) setLoading(false)
      }
    }
    void load()
    return () => {
      cancelled = true
    }
  }, [targetId, selectedId])

  return (
    <div className="terrain-root" role="region" aria-label="3D terrain comparison">
      <div className="terrain-controls">
        <label>
          Vertical exaggeration
          <input
            type="range"
            min={0.2}
            max={4}
            step={0.1}
            value={exaggeration}
            onChange={(e) => setExaggeration(Number(e.target.value))}
          />
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{exaggeration.toFixed(1)}×</span>
        </label>
        <label>
          Sun azimuth
          <input
            type="range"
            min={0}
            max={360}
            step={1}
            value={sunAzimuth}
            onChange={(e) => setSunAzimuth(Number(e.target.value))}
          />
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{sunAzimuth}°</span>
        </label>
        <label>
          Sun elevation
          <input
            type="range"
            min={5}
            max={85}
            step={1}
            value={sunElevation}
            onChange={(e) => setSunElevation(Number(e.target.value))}
          />
          <span style={{ fontVariantNumeric: 'tabular-nums' }}>{sunElevation}°</span>
        </label>
        {loading && <span className="mock-note">Loading heightfields…</span>}
        {error && (
          <span className="status-msg error" style={{ padding: 0 }}>
            {error}
          </span>
        )}
      </div>

      <div className="terrain-panes">
        <div className="terrain-pane">
          <div className="terrain-caption">
            Target · {target?.name ?? '—'}
          </div>
          {targetGrid ? (
            <Canvas camera={{ position: [8, 7, 8], fov: 45 }}>
              <TerrainScene
                grid={targetGrid}
                exaggeration={exaggeration}
                sunAzimuth={sunAzimuth}
                sunElevation={sunElevation}
              />
            </Canvas>
          ) : (
            <div className="terrain-empty">Select a target to load terrain.</div>
          )}
        </div>
        <div className="terrain-pane">
          <div className="terrain-caption">
            Analogue · {selected?.candidate.name ?? 'none selected'}
          </div>
          {resultGrid ? (
            <Canvas camera={{ position: [8, 7, 8], fov: 45 }}>
              <TerrainScene
                grid={resultGrid}
                exaggeration={exaggeration}
                sunAzimuth={sunAzimuth}
                sunElevation={sunElevation}
              />
            </Canvas>
          ) : (
            <div className="terrain-empty">
              Run a search and select a result to compare terrain.
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
