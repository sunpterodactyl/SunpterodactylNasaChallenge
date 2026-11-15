"""M2 validation (SPEC section 11). Run after fit_model.py:  python pipeline/validate.py

1. Synthetic checks: ridge rotation invariance, self-match near 1, flat vs rugged low.
2. Region-blocked landform check: precision at 5 for random, Euclidean baseline,
   texture only, profile only and combined fidelity.
3. Bootstrap stability of each target's top 3 regions.
"""

import sys
from pathlib import Path

import numpy as np

ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

from common import aligned_profile, patch_features  # noqa: E402
from backend.model import (combine, get_model, magnitude_dist, pct,  # noqa: E402
                           profile_dist, texture_dist, transform_texture)

RNG = np.random.default_rng(0)
ALL = ('profile', 'texture', 'magnitude')


def synthetic(m):
    print('\n[Synthetic checks]')
    y, x = np.mgrid[0:64, 0:64] - 31.5

    def ridge(a):
        t = np.radians(a)
        return 100 * np.exp(-((x * np.cos(t) + y * np.sin(t)) / 6) ** 2)

    angles = [0, 20, 45, 70, 90, 135]
    P = np.stack([aligned_profile(ridge(a)) for a in angles])
    d = profile_dist(P, P[0])
    flat_d = profile_dist(np.stack([aligned_profile(np.zeros((64, 64)) + RNG.normal(0, .1, (64, 64)))]), P[0])
    print(f'  ridge profile distance to 0 deg, by angle {angles}: {np.round(d, 4).tolist()} '
          f'(noise patch: {flat_d[0]:.3f})')
    print(f'  profile ptp by angle: {[round(float(np.ptp(p)), 1) for p in P]} (must all be ~100: cuts across ridge)')

    # Identical patch: query an Earth patch with its own features.
    i = 0
    prof, tex, mag = patch_features(m.grid[i].astype(float))
    dd = {'profile': profile_dist(m.profiles, prof),
          'texture': texture_dist(m.Tz, m.zscore(tex), m.icov),
          'magnitude': magnitude_dist(m.mag, mag)}
    F = combine({c: pct(dd[c]) for c in ALL}, ALL)
    print(f'  identical patch {m.patch_id[i]}: F = {F[i]:.3f} (rank {int((F > F[i]).sum()) + 1} of {len(F)})')

    # Flat vs rugged: the flattest patch as query, score of the most rugged patch.
    relief = m.mag[:, 0]
    flat, rugged = int(np.argmin(relief)), int(np.argmax(relief))
    prof, tex, mag = m.profiles[flat], m.a['earth_texture'][flat], m.mag[flat]
    dd = {'profile': profile_dist(m.profiles, prof),
          'texture': texture_dist(m.Tz, m.zscore(tex), m.icov),
          'magnitude': magnitude_dist(m.mag, mag)}
    F = combine({c: pct(dd[c]) for c in ALL}, ALL)
    print(f'  flat {m.patch_id[flat]} vs rugged {m.patch_id[rugged]}: F = {F[rugged]:.3f}')


def region_blocked(m):
    print('\n[Region-blocked landform check: precision at 5]')
    kind = m.a['kind']
    regions = np.unique(m.region)
    kind_of = {r: kind[m.region == r][0] for r in regions}
    T_raw = m.a['earth_texture']
    # Euclidean baseline on z-scored (texture + log magnitude) features
    E_all = np.c_[transform_texture(T_raw, m.log_cols), np.log(np.maximum(m.mag, [1, .1]))]

    methods = ('random', 'euclidean', 'texture', 'profile', 'combined')
    scores = {k: [] for k in methods}
    for r in regions:
        test, train = m.region == r, m.region != r
        others = [o for o in regions if o != r]
        same = np.array([kind_of[o] == kind_of[r] for o in others])
        scores['random'].append(min(same.sum(), 5) / 5 if len(others) <= 5 else same.mean())
        # refit Earth statistics without the held-out region
        X = transform_texture(T_raw[train], m.log_cols)
        mu, sd = X.mean(0), X.std(0) + 1e-12
        Xz = (X - mu) / sd
        icov = np.linalg.inv(np.cov(Xz, rowvar=False) + 1e-2 * np.eye(X.shape[1]))
        E = E_all[train]
        emu, esd = E.mean(0), E.std(0) + 1e-12
        tr_region = m.region[train]
        agg = {k: np.zeros(len(others)) for k in methods[1:]}
        for q in np.where(test)[0]:
            qz = (transform_texture(T_raw[q], m.log_cols) - mu) / sd
            d = {'texture': texture_dist(Xz, qz, icov),
                 'profile': profile_dist(m.profiles[train], m.profiles[q]),
                 'magnitude': magnitude_dist(m.mag[train], m.mag[q])}
            c = {k: pct(v) for k, v in d.items()}
            s = {'euclidean': -np.linalg.norm((E - emu) / esd - (E_all[q] - emu) / esd, axis=1),
                 'texture': c['texture'], 'profile': c['profile'], 'combined': combine(c, ALL)}
            for k, v in s.items():   # region score = best patch score in that region
                agg[k] += np.array([v[tr_region == o].max() for o in others])
        for k, v in agg.items():
            top = np.argsort(-v)[:5]
            scores[k].append(same[top].mean())

    print(f'  {"method":<12}{"P@5":>8}')
    for k in methods:
        print(f'  {k:<12}{np.mean(scores[k]):8.3f}')
    print('  (mean over held-out regions; random = share of other regions with the same kind)')
    return {k: float(np.mean(v)) for k, v in scores.items()}


def stability(m, n_boot=30):
    print('\n[Bootstrap stability of top 3 regions, combined fidelity, all components]')
    regions = np.unique(m.region)
    for tid in m.target_ids:
        d = m.distances(tid)

        def top3(idx):
            F = combine({c: pct(d[c][idx]) for c in ALL}, ALL)
            reg = m.region[idx]
            best = {r: F[reg == r].max() for r in np.unique(reg)}
            return set(sorted(best, key=best.get, reverse=True)[:3])

        base = top3(np.arange(len(m.region)))
        same = 0
        for _ in range(n_boot):
            idx = np.concatenate([RNG.choice(np.where(m.region == r)[0], (m.region == r).sum()) for r in regions])
            same += top3(idx) == base
        print(f'  {tid:<16} top3={sorted(base)}  same in {same}/{n_boot} resamples')


if __name__ == '__main__':
    model = get_model()
    synthetic(model)
    region_blocked(model)
    stability(model)
