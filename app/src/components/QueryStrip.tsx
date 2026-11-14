import { useState } from 'react'
import { useStore } from '../store'
import Sessions from './Sessions'

const VISIBLE_METRICS = 2

export default function QueryStrip() {
  const catalog = useStore((s) => s.catalog)
  const targetId = useStore((s) => s.targetId)
  const setTargetId = useStore((s) => s.setTargetId)
  const metricIds = useStore((s) => s.metricIds)
  const toggleMetric = useStore((s) => s.toggleMetric)
  const weights = useStore((s) => s.weights)
  const setWeight = useStore((s) => s.setWeight)
  const maxCost = useStore((s) => s.maxCost)
  const setMaxCost = useStore((s) => s.setMaxCost)
  const provider = useStore((s) => s.provider)
  const setProvider = useStore((s) => s.setProvider)
  const runSearch = useStore((s) => s.runSearch)
  const searching = useStore((s) => s.searching)
  const rationales = useStore((s) => s.rationales)
  const suggestionSummary = useStore((s) => s.suggestionSummary)
  const [open, setOpen] = useState(false)

  const metrics = catalog?.metrics ?? []
  const primary = metrics.slice(0, VISIBLE_METRICS)
  const extra = metrics.slice(VISIBLE_METRICS)
  const target = catalog?.targets.find((t) => t.id === targetId)
  const moon = catalog?.targets.filter((t) => t.body === 'moon') ?? []
  const mars = catalog?.targets.filter((t) => t.body === 'mars') ?? []

  return (
    <section className={`query-strip${open ? ' open' : ''}`} aria-label="Search filters">
      <div className="strip-row">
        <label className="sim-target">
          <span className="strip-kicker">Target simulation</span>
          <select
            value={targetId}
            onChange={(e) => setTargetId(e.target.value)}
            aria-label="Target site"
          >
            <optgroup label="Moon">
              {moon.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </optgroup>
            <optgroup label="Mars">
              {mars.map((t) => (
                <option key={t.id} value={t.id}>
                  {t.name}
                </option>
              ))}
            </optgroup>
          </select>
          {target && (
            <span className="sim-meta">
              <em>{target.body}</em>
              {target.lat.toFixed(1)}°, {target.lon.toFixed(1)}°
            </span>
          )}
        </label>

        <div className="strip-metrics" aria-label="Primary metrics">
          {primary.map((m) => (
            <MetricControl
              key={m.id}
              id={m.id}
              label={m.label}
              unit={m.unit}
              checked={metricIds.includes(m.id)}
              weight={weights[m.id] ?? 1}
              targetValue={target?.values[m.id]}
              onToggle={() => toggleMetric(m.id)}
              onWeight={(w) => setWeight(m.id, w)}
            />
          ))}
        </div>

        <button
          type="button"
          className="more-btn"
          aria-expanded={open}
          onClick={() => setOpen((v) => !v)}
        >
          {open ? 'Less' : 'More'}
        </button>

        <button
          type="button"
          className="run-btn"
          onClick={() => void runSearch()}
          disabled={searching || !catalog}
        >
          {searching ? 'Searching…' : 'Run search'}
        </button>
      </div>

      {open && (
        <div className="strip-more">
          {suggestionSummary && <p className="suggestion-summary">{suggestionSummary}</p>}

          <div className="strip-metrics">
            {extra.map((m) => (
              <MetricControl
                key={m.id}
                id={m.id}
                label={m.label}
                unit={m.unit}
                checked={metricIds.includes(m.id)}
                weight={weights[m.id] ?? 1}
                targetValue={target?.values[m.id]}
                rationale={rationales[m.id]}
                onToggle={() => toggleMetric(m.id)}
                onWeight={(w) => setWeight(m.id, w)}
              />
            ))}
          </div>

          {primary.some((m) => rationales[m.id]) && (
            <div className="rationale-row">
              {primary
                .filter((m) => rationales[m.id])
                .map((m) => (
                  <p key={m.id} className="rationale">
                    <strong>{m.label}.</strong> {rationales[m.id]}
                  </p>
                ))}
            </div>
          )}

          <div className="strip-extras">
            <label className="cost-control">
              <span>
                Max cost <b>{maxCost.toFixed(2)}</b>
              </span>
              <input
                type="range"
                min={0}
                max={1}
                step={0.05}
                value={maxCost}
                onChange={(e) => setMaxCost(Number(e.target.value))}
                aria-label="Maximum cost index"
              />
            </label>

            <div className="provider-toggle" role="group" aria-label="LLM provider">
              <button
                type="button"
                aria-pressed={provider === 'openai'}
                onClick={() => setProvider('openai')}
              >
                OpenAI
              </button>
              <button
                type="button"
                aria-pressed={provider === 'anthropic'}
                onClick={() => setProvider('anthropic')}
              >
                Claude
              </button>
            </div>
          </div>

          <Sessions />
          <p className="mock-note">Mock metrics — not real measurements.</p>
        </div>
      )}
    </section>
  )
}

function MetricControl({
  id,
  label,
  unit,
  checked,
  weight,
  targetValue,
  rationale,
  onToggle,
  onWeight,
}: {
  id: string
  label: string
  unit: string
  checked: boolean
  weight: number
  targetValue?: number
  rationale?: string
  onToggle: () => void
  onWeight: (w: number) => void
}) {
  return (
    <div className={`metric-pill${checked ? ' on' : ''}`}>
      <label>
        <input type="checkbox" checked={checked} onChange={onToggle} />
        <span>
          {label}
          <small>{unit}</small>
        </span>
      </label>
      {targetValue != null && (
        <span className="target-val" title={`Target ${id}`}>
          {targetValue}
        </span>
      )}
      <input
        type="range"
        min={0}
        max={1}
        step={0.05}
        value={weight}
        disabled={!checked}
        onChange={(e) => onWeight(Number(e.target.value))}
        aria-label={`${label} weight`}
      />
      <span className="weight">{weight.toFixed(2)}</span>
      {rationale && <p className="rationale">{rationale}</p>}
    </div>
  )
}
