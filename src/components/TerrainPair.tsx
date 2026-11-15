import { useEffect, useMemo, useRef } from 'react'
import { Canvas, useThree } from '@react-three/fiber'
import { OrbitControls } from '@react-three/drei'
import type { OrbitControls as OrbitControlsImpl } from 'three-stdlib'
import * as THREE from 'three'
import type { Grid } from '../types'

const SIZE = 10            // scene units across a patch
const PATCH_M = 32000      // metres across a patch (64 x 500 m)
const M_TO_UNITS = SIZE / PATCH_M
const CAMERA_POS: [number, number, number] = [0, 9, 11]
const SUN: [number, number, number] = [-8, 10, -6]   // light from the north-west, like a hillshade

const RAMP = ['#d7d9cf', '#b9bfae', '#8d9886', '#5f6b66', '#33403f'].map((c) => new THREE.Color(c))

function heightColour(t: number) {
  const x = Math.min(Math.max(t, 0), 1) * (RAMP.length - 1)
  const i = Math.min(Math.floor(x), RAMP.length - 2)
  return RAMP[i].clone().lerp(RAMP[i + 1], x - i)
}

function TerrainMesh({ grid, exaggeration }: { grid: Grid; exaggeration: number }) {
  const geometry = useMemo(() => {
    const n = grid.length
    const geo = new THREE.PlaneGeometry(SIZE, SIZE, n - 1, n - 1)
    const pos = geo.attributes.position as THREE.BufferAttribute
    let min = Infinity
    let max = -Infinity
    for (const row of grid) for (const h of row) {
      if (h < min) min = h
      if (h > max) max = h
    }
    const colours = new Float32Array(pos.count * 3)
    for (let i = 0; i < pos.count; i++) {
      const h = grid[Math.floor(i / n)][i % n]
      pos.setZ(i, h * M_TO_UNITS * exaggeration)
      const c = heightColour(max === min ? 0.5 : (h - min) / (max - min))
      colours.set([c.r, c.g, c.b], i * 3)
    }
    geo.setAttribute('color', new THREE.BufferAttribute(colours, 3))
    geo.computeVertexNormals()
    return geo
  }, [grid, exaggeration])

  useEffect(() => () => geometry.dispose(), [geometry])

  return (
    <mesh geometry={geometry} rotation={[-Math.PI / 2, 0, 0]}>
      <meshStandardMaterial vertexColors roughness={0.95} metalness={0} side={THREE.DoubleSide} />
    </mesh>
  )
}

type Hub = {
  views: Record<string, { camera: THREE.Camera; controls: OrbitControlsImpl } | undefined>
  syncing: boolean
}

/** Copies this view's camera to the other view whenever this one moves. */
function CameraSync({ id, hub }: { id: 'a' | 'b'; hub: React.MutableRefObject<Hub> }) {
  const camera = useThree((s) => s.camera)
  const controls = useThree((s) => s.controls) as OrbitControlsImpl | null
  useEffect(() => {
    if (!controls) return
    hub.current.views[id] = { camera, controls }
    const onChange = () => {
      if (hub.current.syncing) return
      const other = hub.current.views[id === 'a' ? 'b' : 'a']
      if (!other) return
      hub.current.syncing = true
      other.camera.position.copy(camera.position)
      other.controls.target.copy(controls.target)
      other.controls.update()
      hub.current.syncing = false
    }
    controls.addEventListener('change', onChange)
    return () => {
      controls.removeEventListener('change', onChange)
      hub.current.views[id] = undefined
    }
  }, [camera, controls, hub, id])
  return null
}

function View({ id, grid, exaggeration, hub, reducedMotion }: {
  id: 'a' | 'b'
  grid: Grid
  exaggeration: number
  hub: React.MutableRefObject<Hub>
  reducedMotion: boolean
}) {
  return (
    <Canvas camera={{ position: CAMERA_POS, fov: 40 }} dpr={[1, 2]}>
      <color attach="background" args={['#eef0ea']} />
      <ambientLight intensity={0.55} />
      <directionalLight position={SUN} intensity={1.6} />
      <TerrainMesh grid={grid} exaggeration={exaggeration} />
      <OrbitControls makeDefault enableDamping={!reducedMotion} maxPolarAngle={Math.PI / 2.05} minDistance={4} maxDistance={30} />
      <CameraSync id={id} hub={hub} />
    </Canvas>
  )
}

interface Props {
  target: { name: string; grid: Grid } | null
  match: { label: string; grid: Grid } | null
  exaggeration: number
  onExaggeration: (v: number) => void
}

export default function TerrainPair({ target, match, exaggeration, onExaggeration }: Props) {
  const hub = useRef<Hub>({ views: {}, syncing: false })
  const reducedMotion = useMemo(
    () => typeof window !== 'undefined' && window.matchMedia?.('(prefers-reduced-motion: reduce)').matches,
    [],
  )

  return (
    <section className="terrain" aria-label="3D terrain comparison">
      <div className="terrain-grid">
        <figure className="pane pane-target">
          <figcaption>
            <span className="swatch target" aria-hidden /> Target · {target?.name ?? '—'}
          </figcaption>
          <div className="canvas-wrap">
            {target ? <View id="a" grid={target.grid} exaggeration={exaggeration} hub={hub} reducedMotion={reducedMotion} />
              : <p className="pane-empty">Pick a target.</p>}
          </div>
        </figure>
        <figure className="pane pane-match">
          <figcaption>
            <span className="swatch match" aria-hidden /> Earth match · {match?.label ?? '—'}
          </figcaption>
          <div className="canvas-wrap">
            {match ? <View id="b" grid={match.grid} exaggeration={exaggeration} hub={hub} reducedMotion={reducedMotion} />
              : <p className="pane-empty">Run a search, then pick a match.</p>}
          </div>
        </figure>
      </div>
      <div className="terrain-controls">
        <label>
          Vertical exaggeration <b className="num">{exaggeration}×</b>
          <input type="range" min={1} max={20} step={1} value={exaggeration}
            onChange={(e) => onExaggeration(Number(e.target.value))} />
        </label>
        <small className="hint">Both 32 × 32 km at 500 m, heights relative to patch median, same scale and light. Drag to orbit; views move together.</small>
      </div>
    </section>
  )
}
