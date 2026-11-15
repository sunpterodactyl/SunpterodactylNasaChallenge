"""CLI search.

python -m backend.search --target marius_hills --objective mobility --stage early
(omit --target to run every target)
"""

import argparse

from backend.model import COMPONENTS, get_model
from backend.scoring import OBJECTIVES, STAGES, Brief, search


def fmt(v):
    return f'{v:5.2f}' if v is not None else '   - '


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', choices=get_model().target_ids)
    ap.add_argument('--objective', default='mobility', choices=list(OBJECTIVES))
    ap.add_argument('--stage', default='early', choices=list(STAGES))
    ap.add_argument('--mode', default='shape_magnitude', choices=['shape', 'shape_magnitude'])
    ap.add_argument('--max-cost-tier', type=int, default=4)
    ap.add_argument('--max-airport-km', type=float, default=1000)
    ap.add_argument('--min-field-months', type=int, default=0)
    ap.add_argument('--k', type=int, default=10)
    a = ap.parse_args()
    for tid in [a.target] if a.target else get_model().target_ids:
        brief = Brief(target_id=tid, objective=a.objective, stage=a.stage, mode=a.mode,
                      max_cost_tier=a.max_cost_tier, max_airport_km=a.max_airport_km,
                      min_field_months=a.min_field_months, k=a.k)
        res = search(brief, with_grids=False)
        print(f'\n{tid}  objective={a.objective} stage={a.stage} mode={a.mode}  '
              f'novelty={res["novelty"]}  best F={res["best_fidelity"]:.3f}')
        if res['message']:
            print(f'  note: {res["message"]}')
        print(f'  {"patch":<24}{"F":>6}{"A":>6}{"R":>6}{"C":>6}  {"profile":>7}{"texture":>8}{"magn.":>7}'
              f'  weakest    pareto  airport_km')
        for m in res['matches']:
            c = m['components']
            print(f'  {m["patch_id"]:<24}{fmt(m["F"]):>6}{fmt(m["A"]):>6}{fmt(m["R"]):>6}{fmt(m["C"]):>6}  '
                  + ''.join(f'{c[k]:>{w}.2f}' for k, w in zip(COMPONENTS, (7, 8, 7)))
                  + f'  {m["weakest"]:<10} {"yes" if m["pareto"] else "":<6} {m["airport_km"]:>8.0f}')


if __name__ == '__main__':
    main()
