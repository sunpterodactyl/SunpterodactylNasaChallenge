import type { Category } from '../types'
import { useStore } from '../store'

const CATEGORY_LABELS: Record<Category, string> = {
  terrain: 'Terrain',
  isru: 'ISRU',
  human_factors: 'Human factors',
}

export default function TopBar() {
  const catalog = useStore((s) => s.catalog)
  const categories = useStore((s) => s.categories)
  const toggleCategory = useStore((s) => s.toggleCategory)
  const prompt = useStore((s) => s.prompt)
  const setPrompt = useStore((s) => s.setPrompt)
  const runSuggest = useStore((s) => s.runSuggest)
  const suggesting = useStore((s) => s.suggesting)
  const suggestError = useStore((s) => s.suggestError)
  const viewMode = useStore((s) => s.viewMode)
  const setViewMode = useStore((s) => s.setViewMode)
  const loadingCatalog = useStore((s) => s.loadingCatalog)
  const catalogError = useStore((s) => s.catalogError)

  const cats = catalog?.categories ?? (['terrain', 'isru', 'human_factors'] as Category[])

  return (
    <header className="topbar">
      <div className="brand">
        Analog Finder
        <span>Earth analogues</span>
      </div>

      <form
        className="top-query"
        onSubmit={(e) => {
          e.preventDefault()
          void runSuggest()
        }}
      >
        <label htmlFor="workflow-prompt">Workflow</label>
        <input
          id="workflow-prompt"
          type="text"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder="Describe the workflow you want to simulate…"
        />
        <button type="submit" disabled={suggesting}>
          {suggesting ? 'Suggesting…' : 'Suggest'}
        </button>
      </form>

      <div className="top-cats" role="group" aria-label="Categories">
        {cats.map((c) => (
          <button
            key={c}
            type="button"
            className="chip"
            aria-pressed={categories.includes(c)}
            onClick={() => toggleCategory(c)}
          >
            {CATEGORY_LABELS[c]}
          </button>
        ))}
      </div>

      <div className="view-toggle" role="tablist" aria-label="View">
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === 'map'}
          onClick={() => setViewMode('map')}
        >
          Map
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={viewMode === 'terrain'}
          onClick={() => setViewMode('terrain')}
        >
          3D
        </button>
      </div>

      {loadingCatalog && <span className="top-note">Loading…</span>}
      {catalogError && (
        <span className="top-note error" role="alert">
          {catalogError}
        </span>
      )}
      {suggestError && (
        <span className="top-note error" role="alert">
          {suggestError}
        </span>
      )}
    </header>
  )
}
