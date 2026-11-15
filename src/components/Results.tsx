import type { Component, Match, Novelty, SearchResult } from '../types'
import Radar from './Radar'

const NOVELTY_TEXT: Record<Novelty, string> = {
  known: 'Known: Earth has close texture matches for this target.',
  edge: 'Edge: the closest Earth texture is unusual for the corpus. Treat matches with care.',
  novel: 'Novel: no Earth patch is close in texture. Rankings are relative only.',
}

const SCORE_NAME: Record<string, string> = { F: 'Fidelity', A: 'Accessibility', R: 'Repeatability', C: 'Affordability' }

function fmt(v: number | null) {
  return v == null ? '–' : v.toFixed(2)
}

function Bar({ k, v }: { k: string; v: number | null }) {
  return (
    <div className="bar" title={`${SCORE_NAME[k]}: ${v == null ? 'not curated yet' : v.toFixed(3)}`}>
      <span className="bar-k">{k}</span>
      <span className={`bar-track ${v == null ? 'unknown' : ''}`}>
        <span className={`bar-fill ${k === 'F' ? 'f' : ''}`} style={{ width: `${(v ?? 0) * 100}%` }} />
      </span>
      <span className="bar-v num">{fmt(v)}</span>
    </div>
  )
}

function NoveltyBadge({ n }: { n: Novelty }) {
  return <span className={`badge novelty-${n}`}>{n}</span>
}

function Detail({ m, starred, onStar }: { m: Match; starred: boolean; onStar: () => void }) {
  const comps = Object.entries(m.components) as [Component, number][]
  return (
    <div className="detail">
      <div className="detail-head">
        <div>
          <h3>{m.patch_id}</h3>
          <p className="muted num">
            {m.lat.toFixed(3)}, {m.lon.toFixed(3)} · {m.kind}
          </p>
        </div>
        <button className={`star ${starred ? 'on' : ''}`} aria-pressed={starred} onClick={onStar}>
          {starred ? '★ Starred' : '☆ Star'}
        </button>
      </div>
      <div className="detail-body">
        <Radar axes={(['F', 'A', 'R', 'C'] as const).map((k) => ({ key: k, label: SCORE_NAME[k], value: m[k] }))} />
        <div className="components">
          <h4>Fidelity components</h4>
          {comps.map(([k, v]) => (
            <div key={k} className={`comp ${k === m.weakest ? 'weakest' : ''}`}>
              <span>{k}</span>
              <span className="bar-track">
                <span className="bar-fill" style={{ width: `${v * 100}%` }} />
              </span>
              <span className="num">{v.toFixed(2)}</span>
            </div>
          ))}
          <p className="muted small">
            Weakest active component: <b>{m.weakest}</b>. Each is the share of Earth patches that are farther from the target.
          </p>
        </div>
      </div>
      <dl className="facts">
        <dt>Nearest airport</dt>
        <dd className="num">{m.airport_km.toFixed(0)} km</dd>
        <dt>Field season</dt>
        <dd>{m.field_months == null ? 'not curated' : `${m.field_months} months`}</dd>
        <dt>Cost tier</dt>
        <dd>{m.cost_tier == null ? 'not curated' : `${m.cost_tier} of 4`}</dd>
        <dt>Permit</dt>
        <dd>{m.permit == null ? 'not curated' : m.permit ? 'required' : 'not required'}</dd>
      </dl>
      <p className="source">
        <b>Sources.</b> {m.source} A, R and C are curated estimates, not measurements.
      </p>
    </div>
  )
}

interface Props {
  result: SearchResult | null
  selected: number
  starred: string[]
  onSelect: (i: number) => void
  onStar: (id: string) => void
}

export default function Results({ result, selected, starred, onSelect, onStar }: Props) {
  if (!result) {
    return (
      <section className="results">
        <h2>Matches</h2>
        <p className="empty-note">Set a brief and run a search to rank Earth patches.</p>
      </section>
    )
  }
  const m = result.matches[selected]
  return (
    <section className="results" aria-live="polite">
      <div className="results-head">
        <h2>Matches</h2>
        <NoveltyBadge n={result.novelty} />
      </div>
      <p className={`novelty-note novelty-${result.novelty}`}>{NOVELTY_TEXT[result.novelty]}</p>
      {result.message && <p className="message">{result.message}</p>}
      {result.matches.length === 0 ? (
        <p className="empty-note">
          Nothing to show. Best fidelity reached: <b className="num">{result.best_fidelity.toFixed(3)}</b>.
        </p>
      ) : (
        <>
          <ol className="match-list">
            {result.matches.map((x, i) => (
              <li key={x.patch_id}>
                <button className={`match-row ${i === selected ? 'selected' : ''}`} aria-current={i === selected}
                  onClick={() => onSelect(i)}>
                  <span className="row-top">
                    <span className="rank num">{i + 1}</span>
                    <span className="region">{x.region.replace(/_/g, ' ')}</span>
                    {starred.includes(x.patch_id) && <span aria-label="starred">★</span>}
                    {x.pareto && <span className="badge pareto" title="Not beaten on every known score by another patch">Pareto</span>}
                    <NoveltyBadge n={result.novelty} />
                  </span>
                  <span className="bars">
                    {(['F', 'A', 'R', 'C'] as const).map((k) => <Bar key={k} k={k} v={x[k]} />)}
                  </span>
                </button>
              </li>
            ))}
          </ol>
          {m && <Detail m={m} starred={starred.includes(m.patch_id)} onStar={() => onStar(m.patch_id)} />}
        </>
      )}
    </section>
  )
}
