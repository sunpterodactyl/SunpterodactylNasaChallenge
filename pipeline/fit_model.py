"""M2: precompute model artifacts for the runtime.

Run from the repo root:  python pipeline/fit_model.py

Reads pipeline/out/earth_patches.npz and targets.npz, computes the profile,
texture and magnitude features (pipeline/common.py), the Earth-only texture
statistics and the novelty thresholds, and writes:
  backend/artifacts/model.npz     arrays the API loads once at import
  backend/artifacts/targets.json  target metadata and 64x64 relative grids
"""

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT))

from common import TEXTURE_LOG, patch_features  # noqa: E402
from backend.model import texture_dist, transform_texture  # noqa: E402

OUT = HERE / 'out'
ART = ROOT / 'backend' / 'artifacts'
RIDGE = 1e-2


def featurise(Z):
    rows = [patch_features(z) for z in Z]
    return (np.stack([r[0] for r in rows]), np.stack([r[1] for r in rows]), np.stack([r[2] for r in rows]))


def texture_stats(T, log_cols):
    X = transform_texture(T, log_cols)
    mean, std = X.mean(0), X.std(0) + 1e-12
    Xz = (X - mean) / std
    cov = np.cov(Xz, rowvar=False) + RIDGE * np.eye(X.shape[1])
    return mean, std, np.linalg.inv(cov), Xz


def novelty_thresholds(Xz, icov, region):
    """Median and p95 of each patch's nearest texture neighbour in a DIFFERENT region."""
    nn = np.empty(len(Xz))
    for i in range(len(Xz)):
        d = texture_dist(Xz, Xz[i], icov)
        d[region == region[i]] = np.inf
        nn[i] = d.min()
    return float(np.median(nn)), float(np.percentile(nn, 95))


def relative_grid(z):
    return np.round(z - np.median(z)).astype(np.int16)


def main():
    e = np.load(OUT / 'earth_patches.npz')
    t = np.load(OUT / 'targets.npz')
    log_cols = np.array(TEXTURE_LOG)

    print(f'Featurising {len(e["z"])} Earth patches and {len(t["z"])} targets...')
    e_prof, e_tex, e_mag = featurise(e['z'])
    t_prof, t_tex, t_mag = featurise(t['z'])
    mean, std, icov, Xz = texture_stats(e_tex, log_cols)
    lo, hi = novelty_thresholds(Xz, icov, e['region'])
    print(f'Novelty thresholds (texture distance): known <= {lo:.3f}, edge <= {hi:.3f}')

    ART.mkdir(parents=True, exist_ok=True)
    np.savez_compressed(
        ART / 'model.npz',
        patch_id=e['patch_id'], region=e['region'], kind=e['kind'], lat=e['lat'], lon=e['lon'],
        earth_grid=np.stack([relative_grid(z) for z in e['z']]),
        earth_profile=e_prof, earth_texture=e_tex, earth_mag=e_mag,
        tex_log_cols=log_cols, tex_mean=mean, tex_std=std, tex_icov=icov,
        novelty_lo=lo, novelty_hi=hi,
        target_id=t['id'], target_profile=t_prof, target_texture=t_tex, target_mag=t_mag,
        earth_source=e['source'],
    )
    targets = [dict(id=str(t['id'][i]), name=str(t['name'][i]), body=str(t['body'][i]),
                    lat=float(t['lat'][i]), lon=float(t['lon'][i]), source=str(t['source']),
                    grid=relative_grid(t['z'][i]).tolist())
               for i in range(len(t['z']))]
    (ART / 'targets.json').write_text(json.dumps(targets, separators=(',', ':')))
    for f in ('model.npz', 'targets.json'):
        print(f'Saved {ART / f} ({(ART / f).stat().st_size / 1e6:.1f} MB)')


if __name__ == '__main__':
    main()
