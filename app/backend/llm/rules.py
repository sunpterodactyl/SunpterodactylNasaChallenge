from typing import Callable
from .models import Target, Candidate, SearchRequest, Match

Filter = Callable[[Candidate, SearchRequest], bool]
FILTERS: list[Filter] = []      # TODO: your hard rules, e.g. slope limits, land cover

def passes(c: Candidate, req: SearchRequest) -> bool:
    if req.categories and c.category not in req.categories:
        return False
    if c.cost_index > req.max_cost:
        return False
    return all(f(c, req) for f in FILTERS)

def score(target: Target, c: Candidate, req: SearchRequest) -> Match:
    # PLACEHOLDER: relative difference per metric, weighted mean. Replace with your logic.
    breakdown, total_w, got_w = {}, 0.0, 0.0
    for m in req.metric_ids:
        w = req.weights.get(m, 1.0)
        total_w += w
        if m in c.values and m in target.values:
            t, v = target.values[m], c.values[m]
            breakdown[m] = max(0.0, 1 - abs(t - v) / (abs(t) + 1e-9)) if t else float(v == 0)
            got_w += w
    s = sum(breakdown[m] * req.weights.get(m, 1.0) for m in breakdown) / got_w if got_w else 0.0
    tiers = {target.evidence.get(m) for m in breakdown}
    tier = 'indirect' if 'indirect' in tiers else ('direct' if tiers else None)
    return Match(candidate=c, score=round(s, 3), coverage=round(got_w / total_w, 3) if total_w else 0.0,
                 breakdown=breakdown, tier=tier)
