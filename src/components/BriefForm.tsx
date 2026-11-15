import type { Brief, Catalog, Mode, Objective, Stage } from '../types'

const OBJECTIVE_LABEL: Record<Objective, string> = {
  mobility: 'Rover mobility',
  navigation: 'Navigation',
  comms_los: 'Comms line of sight',
  eva_traverse: 'EVA traverse',
}

const STAGE_LABEL: Record<Stage, string> = {
  early: 'Early (gate F ≥ 0.5, sort by cost)',
  late: 'Late (gate F ≥ 0.8, sort by fidelity)',
}

interface Props {
  catalog: Catalog
  brief: Brief
  loading: boolean
  onChange: (b: Brief) => void
  onRun: () => void
}

export default function BriefForm({ catalog, brief, loading, onChange, onRun }: Props) {
  const set = <K extends keyof Brief>(k: K, v: Brief[K]) => onChange({ ...brief, [k]: v })
  const bodies = ['moon', 'mars'] as const

  return (
    <form
      className="brief"
      onSubmit={(e) => {
        e.preventDefault()
        onRun()
      }}
    >
      <h2>Test brief</h2>

      <label className="field">
        <span>Target</span>
        <select value={brief.target_id} onChange={(e) => set('target_id', e.target.value)}>
          {bodies.map((body) => {
            const ts = catalog.targets.filter((t) => t.body === body)
            if (!ts.length) return null
            return (
              <optgroup key={body} label={body === 'moon' ? 'Moon' : 'Mars'}>
                {ts.map((t) => (
                  <option key={t.id} value={t.id}>
                    {t.name}
                  </option>
                ))}
              </optgroup>
            )
          })}
        </select>
        {!catalog.targets.some((t) => t.body === 'mars') && (
          <small className="hint">Mars targets are paused: the MOLA data service is returning flat data.</small>
        )}
      </label>

      <label className="field">
        <span>Objective</span>
        <select value={brief.objective} onChange={(e) => set('objective', e.target.value as Objective)}>
          {catalog.objectives.map((o) => (
            <option key={o} value={o}>
              {OBJECTIVE_LABEL[o] ?? o}
            </option>
          ))}
        </select>
      </label>

      <label className="field">
        <span>Stage</span>
        <select value={brief.stage} onChange={(e) => set('stage', e.target.value as Stage)}>
          {catalog.stages.map((s) => (
            <option key={s} value={s}>
              {STAGE_LABEL[s] ?? s}
            </option>
          ))}
        </select>
      </label>

      <fieldset className="field toggle">
        <legend>Fidelity mode</legend>
        {(['shape_magnitude', 'shape'] as Mode[]).map((m) => (
          <label key={m}>
            <input type="radio" name="mode" checked={brief.mode === m} onChange={() => set('mode', m)} />
            {m === 'shape' ? 'Shape only' : 'Shape + magnitude'}
          </label>
        ))}
      </fieldset>

      <details className="filters" open>
        <summary>Filters</summary>
        <label className="field">
          <span>
            Max cost tier <b className="num">{brief.max_cost_tier}</b>
          </span>
          <input type="range" min={1} max={4} step={1} value={brief.max_cost_tier}
            onChange={(e) => set('max_cost_tier', Number(e.target.value))} />
        </label>
        <label className="field">
          <span>
            Max airport distance <b className="num">{brief.max_airport_km} km</b>
          </span>
          <input type="range" min={25} max={1000} step={25} value={brief.max_airport_km}
            onChange={(e) => set('max_airport_km', Number(e.target.value))} />
        </label>
        <label className="field">
          <span>
            Min field season <b className="num">{brief.min_field_months} mo</b>
          </span>
          <input type="range" min={0} max={12} step={1} value={brief.min_field_months}
            onChange={(e) => set('min_field_months', Number(e.target.value))} />
        </label>
        <small className="hint">Regions with uncurated cost or season are excluded once those filters are set.</small>
      </details>

      <button type="submit" className="run" disabled={loading}>
        {loading ? 'Searching…' : 'Run search'}
      </button>
    </form>
  )
}
