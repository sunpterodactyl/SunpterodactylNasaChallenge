"""CLI search.  python -m backend.search --target marius_hills [--objective mobility]"""

import argparse

import numpy as np

from backend.model import COMPONENTS, get_model

OBJECTIVES = {   # PLACEHOLDERS: researcher edits these (SPEC section 7)
    'mobility': ('texture', 'magnitude', 'profile'),
    'navigation': ('profile', 'texture'),
    'comms_los': ('profile', 'magnitude'),
    'eva_traverse': ('magnitude', 'texture'),
}


def main():
    m = get_model()
    ap = argparse.ArgumentParser()
    ap.add_argument('--target', default=None, choices=m.target_ids)
    ap.add_argument('--objective', default='mobility', choices=list(OBJECTIVES))
    ap.add_argument('--k', type=int, default=10)
    args = ap.parse_args()
    for tid in [args.target] if args.target else m.target_ids:
        comps, F, novelty = m.fidelity(tid, OBJECTIVES[args.objective])
        print(f'\n{tid}  objective={args.objective}  novelty={novelty}')
        print(f'  {"patch":<26}{"F":>6}' + ''.join(f'{c:>11}' for c in COMPONENTS))
        for i in np.argsort(-F)[:args.k]:
            print(f'  {m.patch_id[i]:<26}{F[i]:6.3f}' + ''.join(f'{comps[c][i]:11.3f}' for c in COMPONENTS))


if __name__ == '__main__':
    main()
