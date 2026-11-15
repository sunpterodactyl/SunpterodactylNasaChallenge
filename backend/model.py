"""Fidelity model (SPEC section 6). Runtime code: numpy only.

All patch features are precomputed by pipeline/fit_model.py into
backend/artifacts/model.npz. This module only compares a target's
precomputed features against the Earth corpus.
"""

from pathlib import Path

import numpy as np

ARTIFACTS = Path(__file__).parent / 'artifacts'
COMPONENTS = ('profile', 'texture', 'magnitude')
FLOOR = 1e-3


# ---------------------------------------------------------------- distances

def deriv(x):
    """Keogh and Pazzani derivative estimate along the last axis."""
    d = ((x[..., 1:-1] - x[..., :-2]) + (x[..., 2:] - x[..., :-2]) / 2) / 2
    return np.concatenate([d[..., :1], d, d[..., -1:]], axis=-1)


def ddtw_batch(A, b):
    """Derivative DTW from every row of A (P, n) to one series b (m,). Returns (P,)."""
    a, b = deriv(A), deriv(b)
    P, n = a.shape
    m = b.shape[0]
    prev = np.full((P, m + 1), np.inf)
    prev[:, 0] = 0
    for i in range(1, n + 1):
        cost = np.abs(a[:, i - 1:i] - b[None, :])            # (P, m)
        cur = np.full((P, m + 1), np.inf)
        for j in range(1, m + 1):
            cur[:, j] = cost[:, j - 1] + np.minimum(np.minimum(prev[:, j], cur[:, j - 1]), prev[:, j - 1])
        prev = cur
    return prev[:, m] / (n + m)


def normalise_profiles(P):
    return P / (np.ptp(P, axis=-1, keepdims=True) + 1e-9)


def profile_dist(P, t):
    """Shape-only, bidirectional DDTW from each profile in P to target profile t."""
    P, t = normalise_profiles(P), normalise_profiles(t)
    return np.minimum(ddtw_batch(P, t), ddtw_batch(P, t[::-1]))


def transform_texture(T, log_cols):
    T = np.array(T, dtype=np.float64, copy=True)
    T[..., log_cols] = np.log(T[..., log_cols])
    return T


def texture_dist(Tz, tz, icov):
    """Mahalanobis distance between z-scored texture rows Tz (P, k) and tz (k,)."""
    d = Tz - tz
    return np.sqrt(np.einsum('pi,ij,pj->p', d, icov, d))


def magnitude_dist(M, m):
    """|log relief ratio| + |log slope_p90 ratio|. Small floors keep flat salt pans finite."""
    M = np.maximum(M, [1.0, 0.1])
    m = np.maximum(m, [1.0, 0.1])
    return np.abs(np.log(M[:, 0] / m[0])) + np.abs(np.log(M[:, 1] / m[1]))


def pct(d_all):
    """For each patch: share of Earth patches farther from the target than it is."""
    s = np.sort(d_all)
    return (len(s) - np.searchsorted(s, d_all, side='right')) / len(s)


def combine(comps, active):
    """Geometric mean of the active percentile components (no weights)."""
    logs = [np.log(np.maximum(comps[c], FLOOR)) for c in active]
    return np.exp(np.mean(logs, axis=0))


# ---------------------------------------------------------------- model

class Model:
    def __init__(self, path=ARTIFACTS / 'model.npz'):
        a = np.load(path)
        self.a = a
        self.patch_id = a['patch_id']
        self.region = a['region']
        self.lat, self.lon = a['lat'], a['lon']
        self.grid = a['earth_grid']                    # int16 metres, relative to patch median
        self.profiles = a['earth_profile']
        self.log_cols = a['tex_log_cols']
        self.tex_mean, self.tex_std, self.icov = a['tex_mean'], a['tex_std'], a['tex_icov']
        self.Tz = self.zscore(a['earth_texture'])
        self.mag = a['earth_mag']
        self.nov_lo, self.nov_hi = float(a['novelty_lo']), float(a['novelty_hi'])
        self.target_ids = list(a['target_id'])
        self.t_profile, self.t_texture, self.t_mag = a['target_profile'], a['target_texture'], a['target_mag']
        # Optional exploration set: bare-terrain patches outside the curated regions.
        self.explore = None
        if (path.parent / 'explore.npz').exists():
            x = np.load(path.parent / 'explore.npz')
            self.explore = dict(x)
            self.explore['Tz'] = self.zscore(x['texture'])

    def zscore(self, T):
        return (transform_texture(T, self.log_cols) - self.tex_mean) / self.tex_std

    def distances(self, target_id, which='known'):
        """Raw component distances from the target to every patch in the known or explore set."""
        i = self.target_ids.index(target_id)
        if which == 'known':
            P, Tz, M = self.profiles, self.Tz, self.mag
        else:
            P, Tz, M = self.explore['profile'], self.explore['Tz'], self.explore['mag']
        return {
            'profile': profile_dist(P, self.t_profile[i]),
            'texture': texture_dist(Tz, self.zscore(self.t_texture[i]), self.icov),
            'magnitude': magnitude_dist(M, self.t_mag[i]),
        }

    def novelty(self, d_texture):
        best = float(d_texture.min())
        return 'known' if best <= self.nov_lo else 'edge' if best <= self.nov_hi else 'novel'

    def fidelity(self, target_id, active):
        """Per-patch percentile components, combined F, and the novelty flag."""
        d = self.distances(target_id)
        comps = {c: pct(d[c]) for c in COMPONENTS}
        return comps, combine(comps, active), self.novelty(d['texture'])


_MODEL = None


def get_model():
    global _MODEL
    if _MODEL is None:
        _MODEL = Model()
    return _MODEL
