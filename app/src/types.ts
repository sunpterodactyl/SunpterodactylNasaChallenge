export type Category = 'terrain' | 'isru' | 'human_factors'
export type Evidence = 'direct' | 'indirect'
export type Provider = 'openai' | 'anthropic'

export interface Metric {
  id: string
  label: string
  unit: string
  description: string
}

export interface Target {
  id: string
  body: 'moon' | 'mars'
  name: string
  lat: number
  lon: number
  values: Record<string, number>
  evidence: Record<string, Evidence>
}

export interface Candidate {
  id: string
  name: string
  country: string
  lat: number
  lon: number
  category: Category
  cost_index: number
  values: Record<string, number>
}

export interface SearchRequest {
  target_id: string
  metric_ids: string[]
  weights: Record<string, number>
  categories: Category[]
  max_cost: number
  prompt?: string | null
}

export interface Match {
  candidate: Candidate
  score: number
  coverage: number
  breakdown: Record<string, number>
  tier: Evidence | null
}

export interface MetricPick {
  metric_id: string
  weight: number
  rationale: string
}

export interface Suggestion {
  picks: MetricPick[]
  categories: Category[]
  summary: string
}

export interface Catalog {
  metrics: Metric[]
  targets: Target[]
  categories: Category[]
}

export interface Session {
  id: string
  name: string
  createdAt: string
  request: SearchRequest & { provider?: Provider }
  starred: string[]
  notes: Record<string, string>
}
