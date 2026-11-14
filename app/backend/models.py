from typing import Literal
from pydantic import BaseModel, Field

Category = Literal['terrain', 'isru', 'human_factors']
Evidence = Literal['direct', 'indirect']

class Metric(BaseModel):
    id: str
    label: str
    unit: str
    description: str

class Target(BaseModel):
    id: str
    body: Literal['moon', 'mars']
    name: str
    lat: float
    lon: float
    values: dict[str, float]          # metric_id -> value
    evidence: dict[str, Evidence]     # metric_id -> direct | indirect

class Candidate(BaseModel):
    id: str
    name: str
    country: str
    lat: float
    lon: float
    category: Category
    cost_index: float = Field(ge=0, le=1)   # 0 cheap, 1 expensive (mock)
    values: dict[str, float]

class SearchRequest(BaseModel):
    target_id: str
    metric_ids: list[str]
    weights: dict[str, float] = {}
    categories: list[Category] = []
    max_cost: float = 1.0
    prompt: str | None = None

class Match(BaseModel):
    candidate: Candidate
    score: float                       # 0..1
    coverage: float                    # share of requested weight with data
    breakdown: dict[str, float]        # metric_id -> per-metric similarity
    tier: Evidence | None = None       # first-order (direct) vs second-order (indirect)

class MetricPick(BaseModel):
    metric_id: str
    weight: float = Field(ge=0, le=1)
    rationale: str

class Suggestion(BaseModel):
    picks: list[MetricPick]
    categories: list[Category] = []
    summary: str
