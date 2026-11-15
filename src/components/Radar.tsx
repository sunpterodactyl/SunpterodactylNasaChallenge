type Axis = { key: string; label: string; value: number | null }

/** Four-axis radar (F, A, R, C). Unknown values sit at the centre, drawn hollow and labelled n/a. */
export default function Radar({ axes, size = 180 }: { axes: Axis[]; size?: number }) {
  const c = size / 2
  const r = c - 28
  const pt = (i: number, v: number) => {
    const a = -Math.PI / 2 + (i * 2 * Math.PI) / axes.length
    return [c + Math.cos(a) * r * v, c + Math.sin(a) * r * v] as const
  }
  const poly = axes.map((ax, i) => pt(i, ax.value ?? 0).join(',')).join(' ')
  const desc = axes.map((a) => `${a.label} ${a.value == null ? 'not available' : a.value.toFixed(2)}`).join(', ')

  return (
    <svg className="radar" viewBox={`0 0 ${size} ${size}`} width={size} height={size} role="img" aria-label={`Scores: ${desc}`}>
      {[0.25, 0.5, 0.75, 1].map((s) => (
        <polygon key={s} className="radar-ring" points={axes.map((_, i) => pt(i, s).join(',')).join(' ')} />
      ))}
      {axes.map((_, i) => {
        const [x, y] = pt(i, 1)
        return <line key={i} className="radar-spoke" x1={c} y1={c} x2={x} y2={y} />
      })}
      <polygon className="radar-shape" points={poly} />
      {axes.map((ax, i) => {
        const [x, y] = pt(i, ax.value ?? 0)
        const [lx, ly] = pt(i, 1.22)
        return (
          <g key={ax.key}>
            <circle cx={x} cy={y} r={3} className={ax.value == null ? 'radar-dot unknown' : 'radar-dot'} />
            <text x={lx} y={ly} className="radar-label" textAnchor="middle" dominantBaseline="middle">
              {ax.key} {ax.value == null ? 'n/a' : ax.value.toFixed(2)}
            </text>
          </g>
        )
      })}
    </svg>
  )
}
