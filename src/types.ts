export type Grid = number[][]

export type Objective = 'mobility' | 'navigation' | 'comms_los' | 'eva_traverse'
export type Stage = 'early' | 'late'
export type Mode = 'shape' | 'shape_magnitude'
export type Novelty = 'known' | 'edge' | 'novel'
export type Component = 'profile' | 'texture' | 'magnitude'

export interface Target {
  id: string
  name: string
  body: 'moon' | 'mars'
  lat: number
  lon: number
  grid: Grid
}

export interface Catalog {
  targets: Target[]
  objectives: Objective[]
  stages: Stage[]
  regions: string[]
}

export interface Brief {
  target_id: string
  objective: Objective
  stage: Stage
  mode: Mode
  max_cost_tier: number
  max_airport_km: number
  min_field_months: number
  k: number
}

export interface Match {
  patch_id: string
  region: string
  lat: number
  lon: number
  kind: string
  F: number
  A: number
  R: number | null
  C: number | null
  components: Record<Component, number>
  weakest: Component
  pareto: boolean
  airport_km: number
  field_months: number | null
  cost_tier: number | null
  permit: boolean | null
  source: string
  grid: Grid
}

export interface SearchResult {
  target_id: string
  novelty: Novelty
  best_fidelity: number
  message: string | null
  matches: Match[]
}

export interface Session {
  name: string
  brief: Brief
  starred: string[]
  notes: string
  saved_at: string
}
