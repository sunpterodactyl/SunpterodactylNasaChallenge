import { create } from 'zustand'
import * as api from './api'
import type {
  Catalog,
  Category,
  Match,
  Provider,
  SearchRequest,
  Session,
  Suggestion,
} from './types'

const SESSIONS_KEY = 'analog.sessions'

function loadSessions(): Session[] {
  try {
    const raw = localStorage.getItem(SESSIONS_KEY)
    return raw ? (JSON.parse(raw) as Session[]) : []
  } catch {
    return []
  }
}

function persistSessions(sessions: Session[]) {
  localStorage.setItem(SESSIONS_KEY, JSON.stringify(sessions))
}

interface AppState {
  catalog: Catalog | null
  catalogError: string | null
  loadingCatalog: boolean

  targetId: string
  metricIds: string[]
  weights: Record<string, number>
  categories: Category[]
  maxCost: number
  prompt: string
  provider: Provider
  rationales: Record<string, string>
  suggestionSummary: string | null

  results: Match[]
  selectedId: string | null
  searching: boolean
  suggesting: boolean
  searchError: string | null
  suggestError: string | null
  viewMode: 'map' | 'terrain'

  starred: string[]
  notes: Record<string, string>
  sessions: Session[]

  loadCatalog: () => Promise<void>
  setTargetId: (id: string) => void
  toggleMetric: (id: string) => void
  setWeight: (id: string, w: number) => void
  toggleCategory: (c: Category) => void
  setMaxCost: (v: number) => void
  setPrompt: (v: string) => void
  setProvider: (p: Provider) => void
  setViewMode: (m: 'map' | 'terrain') => void
  setSelectedId: (id: string | null) => void
  toggleStar: (id: string) => void
  setNote: (id: string, note: string) => void
  buildRequest: () => SearchRequest
  runSearch: () => Promise<void>
  runSuggest: () => Promise<void>
  applySuggestion: (s: Suggestion) => void
  saveSession: (name: string) => void
  openSession: (id: string) => Promise<void>
  renameSession: (id: string, name: string) => void
  deleteSession: (id: string) => void
  exportSession: (id: string) => void
}

export const useStore = create<AppState>((set, get) => ({
  catalog: null,
  catalogError: null,
  loadingCatalog: false,

  targetId: '',
  metricIds: [],
  weights: {},
  categories: [],
  maxCost: 1.0,
  prompt: '',
  provider: 'openai',
  rationales: {},
  suggestionSummary: null,

  results: [],
  selectedId: null,
  searching: false,
  suggesting: false,
  searchError: null,
  suggestError: null,
  viewMode: 'map',

  starred: [],
  notes: {},
  sessions: loadSessions(),

  loadCatalog: async () => {
    set({ loadingCatalog: true, catalogError: null })
    try {
      const catalog = await api.fetchCatalog()
      const state = get()
      set({
        catalog,
        loadingCatalog: false,
        targetId: state.targetId || catalog.targets[0]?.id || '',
        metricIds:
          state.metricIds.length > 0
            ? state.metricIds
            : catalog.metrics.map((m) => m.id),
        weights:
          Object.keys(state.weights).length > 0
            ? state.weights
            : Object.fromEntries(catalog.metrics.map((m) => [m.id, 1])),
      })
    } catch (e) {
      set({
        loadingCatalog: false,
        catalogError: e instanceof Error ? e.message : String(e),
      })
    }
  },

  setTargetId: (id) => set({ targetId: id }),

  toggleMetric: (id) => {
    const { metricIds, weights } = get()
    if (metricIds.includes(id)) {
      set({ metricIds: metricIds.filter((m) => m !== id) })
    } else {
      set({
        metricIds: [...metricIds, id],
        weights: { ...weights, [id]: weights[id] ?? 1 },
      })
    }
  },

  setWeight: (id, w) =>
    set({ weights: { ...get().weights, [id]: Math.min(1, Math.max(0, w)) } }),

  toggleCategory: (c) => {
    const { categories } = get()
    set({
      categories: categories.includes(c)
        ? categories.filter((x) => x !== c)
        : [...categories, c],
    })
  },

  setMaxCost: (v) => set({ maxCost: v }),
  setPrompt: (v) => set({ prompt: v }),
  setProvider: (p) => set({ provider: p }),
  setViewMode: (m) => set({ viewMode: m }),
  setSelectedId: (id) => set({ selectedId: id }),

  toggleStar: (id) => {
    const { starred } = get()
    set({
      starred: starred.includes(id)
        ? starred.filter((s) => s !== id)
        : [...starred, id],
    })
  },

  setNote: (id, note) => set({ notes: { ...get().notes, [id]: note } }),

  buildRequest: () => {
    const s = get()
    return {
      target_id: s.targetId,
      metric_ids: s.metricIds,
      weights: Object.fromEntries(
        s.metricIds.map((id) => [id, s.weights[id] ?? 1]),
      ),
      categories: s.categories,
      max_cost: s.maxCost,
      prompt: s.prompt || null,
    }
  },

  runSearch: async () => {
    const req = get().buildRequest()
    if (!req.target_id) {
      set({ searchError: 'Select a target site first.' })
      return
    }
    if (req.metric_ids.length === 0) {
      set({ searchError: 'Select at least one metric.' })
      return
    }
    set({ searching: true, searchError: null })
    try {
      const results = await api.search(req)
      set({
        results,
        searching: false,
        selectedId: results[0]?.candidate.id ?? null,
        searchError:
          results.length === 0
            ? 'No analogues matched. Category filters or max cost may have removed every candidate.'
            : null,
      })
    } catch (e) {
      set({
        searching: false,
        searchError: e instanceof Error ? e.message : String(e),
      })
    }
  },

  runSuggest: async () => {
    const { prompt, provider } = get()
    if (!prompt.trim()) {
      set({ suggestError: 'Describe the workflow you want to simulate.' })
      return
    }
    set({ suggesting: true, suggestError: null })
    try {
      const suggestion = await api.suggest(prompt.trim(), provider)
      get().applySuggestion(suggestion)
      set({ suggesting: false })
    } catch (e) {
      set({
        suggesting: false,
        suggestError: e instanceof Error ? e.message : String(e),
      })
    }
  },

  applySuggestion: (s) => {
    const metricIds = s.picks.map((p) => p.metric_id)
    const weights = Object.fromEntries(s.picks.map((p) => [p.metric_id, p.weight]))
    const rationales = Object.fromEntries(
      s.picks.map((p) => [p.metric_id, p.rationale]),
    )
    set({
      metricIds,
      weights: { ...get().weights, ...weights },
      categories: s.categories,
      rationales,
      suggestionSummary: s.summary,
      suggestError: null,
    })
  },

  saveSession: (name) => {
    const s = get()
    const session: Session = {
      id: crypto.randomUUID(),
      name: name.trim() || `Session ${new Date().toLocaleString()}`,
      createdAt: new Date().toISOString(),
      request: { ...s.buildRequest(), provider: s.provider },
      starred: [...s.starred],
      notes: { ...s.notes },
    }
    const sessions = [session, ...s.sessions]
    persistSessions(sessions)
    set({ sessions })
  },

  openSession: async (id) => {
    const session = get().sessions.find((x) => x.id === id)
    if (!session) return
    const r = session.request
    set({
      targetId: r.target_id,
      metricIds: r.metric_ids,
      weights: r.weights,
      categories: r.categories,
      maxCost: r.max_cost,
      prompt: r.prompt ?? '',
      provider: r.provider ?? 'openai',
      starred: [...session.starred],
      notes: { ...session.notes },
      rationales: {},
      suggestionSummary: null,
    })
    await get().runSearch()
  },

  renameSession: (id, name) => {
    const sessions = get().sessions.map((s) =>
      s.id === id ? { ...s, name: name.trim() || s.name } : s,
    )
    persistSessions(sessions)
    set({ sessions })
  },

  deleteSession: (id) => {
    const sessions = get().sessions.filter((s) => s.id !== id)
    persistSessions(sessions)
    set({ sessions })
  },

  exportSession: (id) => {
    const session = get().sessions.find((s) => s.id === id)
    if (!session) return
    const blob = new Blob([JSON.stringify(session, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${session.name.replace(/\s+/g, '_').toLowerCase()}.json`
    a.click()
    URL.revokeObjectURL(url)
  },
}))
