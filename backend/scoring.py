"""Test Brief, A/R/C scores and ranking (SPEC section 7). Runtime code: numpy only.

Curated region values may be blank (None). Rules for unknowns, so that
nothing is invented:
- A uses airport distance (measured). If permit is unknown the permit factor
  is left out and `permit` is returned as None.
- R and C are None when their curated inputs are blank.
- A filter lets an unknown value through only while the filter is at its
  default (non-restrictive) setting.
- If the stage's sort key is unknown for any passing patch, results are sorted
  by F instead and the message says so.
- Pareto is computed over the scores that are known for every patch.
"""

import json
from typing import Literal

import numpy as np
from pydantic import BaseModel

from backend.model import ARTIFACTS, COMPONENTS, get_model

OBJECTIVES = {   # PLACEHOLDERS: researcher edits these
    'mobility': ('texture', 'magnitude', 'profile'),
    'navigation': ('profile', 'texture'),
    'comms_los': ('profile', 'magnitude'),
    'eva_traverse': ('magnitude', 'texture'),
}
STAGES = {       # PLACEHOLDERS: stage changes the rule (gate, sort key), not weights
    'early': dict(gate=0.5, sort='C'),
    'late': dict(gate=0.8, sort='F'),
}
PERMIT_FACTOR = 0.5   # placeholder (SPEC section 7)
SCORES = 'FARC'
DEFAULTS = dict(max_cost_tier=4, max_airport_km=1000, min_field_months=0)


class Brief(BaseModel):
    target_id: str
    objective: Literal['mobility', 'navigation', 'comms_los', 'eva_traverse']
    stage: Literal['early', 'late']
    mode: Literal['shape', 'shape_magnitude'] = 'shape_magnitude'
    max_cost_tier: int = 4
    max_airport_km: float = 1000
    min_field_months: int = 0
    k: int = 10


_REGIONS = None
_TARGETS = None


def regions():
    global _REGIONS
    if _REGIONS is None:
        _REGIONS = {r['region']: r for r in json.loads((ARTIFACTS / 'regions.json').read_text())}
    return _REGIONS


def targets():
    global _TARGETS
    if _TARGETS is None:
        _TARGETS = json.loads((ARTIFACTS / 'targets.json').read_text())
    return _TARGETS


def region_scores(r):
    A = 1 - min(r['airport_km'], 1000) / 1000
    if r['permit'] is not None:
        A *= PERMIT_FACTOR if r['permit'] else 1
    R = (r['field_months'] / 12 * r['stability']
         if r['field_months'] is not None and r['stability'] is not None else None)
    C = (5 - r['cost_tier']) / 4 if r['cost_tier'] is not None else None
    return A, R, C


def source_note(r):
    curated = r['source'] or 'not yet curated (blank in regions.csv)'
    return (f'A: OurAirports, nearest large/medium airport {r["airport"]}, {r["airport_km"]:.0f} km from region centre. '
            f'R, C, permit: {curated}. Terrain: Copernicus DEM GLO-30.')


def active_components(brief):
    active = OBJECTIVES[brief.objective]
    if brief.mode == 'shape':
        active = tuple(c for c in active if c != 'magnitude')
    return active


def passes(m, brief):
    def ok(value, limit, default, cmp):
        if value is None:
            return limit == default
        return cmp(value, limit)
    return (ok(m['cost_tier'], brief.max_cost_tier, DEFAULTS['max_cost_tier'], lambda v, l: v <= l)
            and m['airport_km'] <= brief.max_airport_km
            and ok(m['field_months'], brief.min_field_months, DEFAULTS['min_field_months'], lambda v, l: v >= l))


def mark_pareto(ms):
    keys = [k for k in SCORES if all(m[k] is not None for m in ms)]
    for m in ms:
        m['pareto'] = not any(all(o[k] >= m[k] for k in keys) and any(o[k] > m[k] for k in keys) for o in ms)
    return keys


def rank(ms, brief):
    st = STAGES[brief.stage]
    notes = []
    keys = mark_pareto(ms)
    if set(keys) != set(SCORES):
        notes.append(f'Pareto uses {"/".join(keys)} only; other scores are not curated for every region.')
    ok = [m for m in ms if m['F'] >= st['gate'] and passes(m, brief)]
    sort = st['sort']
    if any(m[sort] is None for m in ok):
        notes.append(f'{brief.stage} stage sorts by {sort}, but {sort} is not curated for every region; sorted by F.')
        sort = 'F'
    ranked = sorted(ok, key=lambda m: (-m[sort], -m['F']))[:brief.k]
    return ranked, notes


def search(brief, with_grids=True):
    model = get_model()
    if brief.target_id not in model.target_ids:
        raise KeyError(brief.target_id)
    active = active_components(brief)
    comps, F, novelty = model.fidelity(brief.target_id, active)
    regs = regions()
    ms = []
    for i in range(len(F)):
        r = regs[str(model.region[i])]
        A, R, C = region_scores(r)
        c = {k: round(float(comps[k][i]), 4) for k in COMPONENTS}
        ms.append(dict(
            idx=i, patch_id=str(model.patch_id[i]), region=r['region'],
            lat=round(float(model.lat[i]), 4), lon=round(float(model.lon[i]), 4), kind=r['kind'],
            F=round(float(F[i]), 4), A=round(A, 4), R=None if R is None else round(R, 4),
            C=None if C is None else round(C, 4),
            components=c, weakest=min(active, key=lambda k: c[k]),
            airport_km=r['airport_km'], field_months=r['field_months'], cost_tier=r['cost_tier'],
            permit=r['permit'], source=source_note(r),
        ))
    ranked, notes = rank(ms, brief)
    best = float(F.max())
    message = None
    if not ranked:
        gate = STAGES[brief.stage]['gate']
        if best < gate:
            message = (f'No Earth patch reaches the {brief.stage}-stage gate (F >= {gate}). '
                       f'Best fidelity reached: {best:.3f}.')
        else:
            message = (f'Patches pass the {brief.stage}-stage gate (best F {best:.3f}), but none pass the '
                       f'cost, airport and season filters. Regions with blank curated values are excluded '
                       f'once a filter on that value is set.')
    elif notes:
        message = ' '.join(notes)
    for m in ranked:
        i = m.pop('idx')
        if with_grids:
            m['grid'] = model.grid[i].tolist()
    return dict(target_id=brief.target_id, novelty=novelty, best_fidelity=round(best, 4),
                message=message, matches=ranked)


def catalog():
    return dict(
        targets=[{k: t[k] for k in ('id', 'name', 'body', 'lat', 'lon', 'grid')} for t in targets()],
        objectives=list(OBJECTIVES), stages=list(STAGES), regions=sorted(regions()),
    )
