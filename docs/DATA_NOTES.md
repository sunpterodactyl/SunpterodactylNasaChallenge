# Data notes (M0)

Findings from `python pipeline/verify_sources.py`, run 2026-11-15. Each
patch is 64 x 64 at 500 m (32 km square). Hillshades are written to
`pipeline/out/m0_*.png` (gitignored).

## Results

| Source | Patch | min / max (m) | std (m) | time | Verdict |
| --- | --- | --- | --- | --- | --- |
| Copernicus GLO-30 (Planetary Computer) | atacama (-24.5, -69.2) | 2032 / 3876 | 390.8 | 5.3 s | PASS |
| USGS WMS `LOLA_elev` | marius_hills (14.1, -56.7) | -1811 / -950 | 127.3 | 6.5 s | PASS |
| USGS WMS `MOLA_elev` | jezero_delta (18.4, 77.5) | -1517 / -1517 | 0.0 | 5.4 s | **FAIL** |
| Astropedia MOLA 463 m mosaic (fallback probe only, not used) | jezero_delta | -2715 / -1586 | 274.5 | 14.3 s | PASS |

**The Mars WMS layer is broken.** `MOLA_elev` returns the single value
-1517 m everywhere: a 360 x 180 request over the whole planet has exactly one
unique value, and the PNG output is flat too. Per CLAUDE.md this is a stop
and report. No Mars data has been substituted. The SPEC section 4 fallback
(Astropedia) is reachable and returns believable relief for Jezero (the crater
rim is visible in the hillshade), but switching to it needs a decision.

## SPEC section 4 UNVERIFIED items

| Item | Status | Evidence |
| --- | --- | --- |
| `http://wms.wr.usgs.gov` endpoint works | **FAILED** | Connection times out. `https://planetarymaps.usgs.gov` serves the same map files and responds in about 5-7 s per request. |
| WMS Int16 units are metres | **CONFIRMED (Moon)** | `LOLA_elev_uint16` (documented as metres + 9130) minus `LOLA_elev` has median 9130, range 9126-9134. The few-metre spread comes from the two layers being resampled separately. Mars cannot be checked while `MOLA_elev` is broken. |
| WMS resampling when requesting fewer pixels | **NOT SETTLED** | Comparing a 64 px request with a 256 px request of the same box: mean difference vs 4x4 block mean is 3.43 m, vs centre-pixel nearest is 3.40 m. Both are equally close, so the method can't be told apart this way. MapServer defaults to nearest neighbour. If we keep using the WMS, request 4x pixels and block-average ourselves so we don't rely on the server's resampling. |
| Mars longitude convention | **INCONCLUSIVE via WMS / -180..180 via Astropedia** | WMS replies are constant at both 77.5 and -282.5. The Astropedia mosaic spans x = -10669675..10669675 m, i.e. -180..180 deg centred on 0. Moon WMS is also -180..180 (lon 303.3 returns all zeros). |
| Copernicus asset key is `data` | **CONFIRMED** | Item assets are `data`, `rendered_preview`, `tilejson`. Tile `Copernicus_DSM_COG_10_S25_00_W070_00_DEM`, EPSG:4326, 1 arcsec, float32. |
| Copernicus is a surface model (includes canopy) | **CONFIRMED (product docs)** | The tile id says `DSM`. The file has no units tag and `nodata=None`, so missing coverage only shows up as cells no tile covered (left as NaN by our reproject). M1's nodata QC must count NaNs, not a nodata value. Regions must be bare terrain. |

## Other notes

- Request the WMS with `VERSION=1.1.1`, `SRS=EPSG:4326` and `BBOX=minlon,minlat,maxlon,maxlat`. In 1.3.0 EPSG:4326 the axis order flips to lat,lon.
- `IAU_2015:49900` is advertised for Mars but returned all zeros in a quick test.
- Astropedia mosaic: `Mars_MGS_MOLA_DEM_mosaic_global_463m.tif`, 23040 x 46080 Int16, nodata -32768, equirectangular metres on a sphere. It is stored in strips (one row per block), so a 32 km window reads about 70 rows x 92 KB remotely. That's fine for 2 targets; for repeated runs, cache a regional crop in `pipeline/data/` as SPEC section 4 says.
- Copernicus reads use `Resampling.average` from 30 m to 500 m, which is a true area average.

## Decisions

- **2026-11-15: Mars targets are left out for now.** `jezero_delta` and `gale` are
  not built while the MOLA WMS layer is broken. v1 runs with the three Moon
  targets only. The Astropedia fallback stays documented above in case Mars
  comes back.
- **Copernicus sea is 0, not nodata.** Checked during M1 prep: a patch over
  the sea off Tenerife is 100% exactly 0.0 m with no NaN, and a Svalbard patch
  is 25% exactly 0.0 (fjords). M1 QC therefore counts exact-zero cells as
  nodata alongside NaN. Real land below sea level (Death Valley, Danakil) is
  negative, not zero, so it is unaffected.
- **Targets are read at 4x and block-averaged.** The WMS resampling method is
  unsettled (see above), so M1 requests 256 x 256 and averages 4 x 4 blocks
  down to 64 x 64. This matches the area average used for Copernicus.

# Corpus build (M1)

`python pipeline/build_corpus.py`, run 2026-11-15, about 1.5 min with 6
region threads. Seed 42, 25 patches per region, jitter +-0.4 deg.

| region | kind | kept | skipped | relief p5-p95, median (m) | status |
| --- | --- | --- | --- | --- | --- |
| atacama | arid | 25 | 0 | 1013 | ok |
| namib | dune | 21 | 4 | 286 | ok |
| gobi | arid | 25 | 0 | 270 | ok |
| lut | arid | 25 | 0 | 168 | ok |
| tibesti | volcanic | 25 | 0 | 868 | ok |
| death_valley | arid | 25 | 0 | 1502 | ok |
| askja | volcanic | 25 | 0 | 622 | ok |
| mauna_loa | volcanic | 16 | 9 | 2217 | ok |
| etna | volcanic | 11 | 14 | 1263 | dropped (<15) |
| craters_of_the_moon | volcanic | 25 | 0 | 244 | ok |
| tenerife | volcanic | 1 | 24 | 2226 | dropped (<15) |
| pinacate | volcanic | 22 | 3 | 207 | ok |
| devon | polar | 18 | 7 | 164 | ok |
| dry_valleys | polar | 24 | 1 | 1519 | ok |
| svalbard | polar | 6 | 19 | 746 | dropped (<15) |
| uyuni | flat | 25 | 0 | 0 | ok |
| bonneville | flat | 25 | 0 | 265 | ok |
| taklamakan | dune | 25 | 0 | 42 | ok |
| rub_al_khali | dune | 25 | 0 | 23 | ok |
| qaidam | arid | 25 | 0 | 38 | ok |
| danakil | volcanic | 25 | 0 | 428 | ok |
| altiplano_north | mountain | 25 | 0 | 875 | ok |

**Kept 451 patches from 19 regions.** No NaN remains; 17 kept patches had
some nodata filled (max 4.5%). Below-sea-level land survives the sea rule
(Danakil min -125 m, Death Valley min -86 m).

Notes:

- **Dropped regions are coastal or island sites.** Jittered patches land in the sea.
  Etna, Tenerife and Svalbard could be kept by moving the centre inland or
  shrinking the jitter. That's a curation choice for the region table.
- **Uyuni is near-perfectly flat.** p5-p95 relief is 0 m in most patches, per-patch
  std about 6 m. This is real (salt flat), but M2 must guard `log(relief)`
  and `slope_p90` against zero.
- **Vegetation:** Etna's and Mauna Loa's lower flanks carry vegetation, which a
  surface model includes. Not filtered.
- **Targets:** marius_hills relief 423 m, taurus_littrow 1982 m,
  tycho_rim 988 m. The `tycho_rim` coordinate (-43.3, -11.4) is Tycho's
  centre. The 32 km patch shows the central peak and floor, not the rim.
  Either rename it or move it about 0.7 deg off-centre onto the rim.

# Fidelity model and validation (M2)

`python pipeline/fit_model.py` then `python pipeline/validate.py`.

- **Rotation sign fixed.** SPEC 6.1 rotates by `-degrees(th)`. With
  `scipy.ndimage.rotate` that leaves the profile running *along* a diagonal
  ridge (profile ptp 0 at 45 and 135 deg). `+degrees(th)` cuts across it at
  every angle (ptp ~99 m for a 100 m ridge), so `common.aligned_profile` uses `+`.
- **Novelty thresholds** (nearest texture neighbour in another region):
  known <= 0.153, edge <= 1.601.

Synthetic checks: ridge profiles at 0/20/45/70/90/135 deg are within 0.0001
DDTW of each other (noise patch: 0.073); an Earth patch queried against itself
scores F = 0.998 (rank 1 of 451); flattest (uyuni_00) vs most rugged
(mauna_loa_00) scores F = 0.150.

Region-blocked precision at 5 (19 held-out regions, region score = best patch):

| method | P@5 |
| --- | --- |
| random | 0.175 |
| Euclidean on z-scored features | 0.200 |
| texture only | 0.232 |
| profile only | **0.274** |
| combined fidelity | 0.253 |

**Honest negative:** combined fidelity beats random and the Euclidean
baseline, but profile-only beats combined. With 19 regions and hand-assigned
kinds, the differences are small and noisy.

Bootstrap stability (30 resamples within regions), top-3 regions unchanged:
marius_hills 10/30, taurus_littrow 18/30, tycho_rim 22/30. Marius Hills' top
three are close in score, so their order is unstable.

# Regions, A/R/C and ranking (M3)

- **Airport distance.** Measured as haversine from each region's centre to the nearest OurAirports
  `large_airport` or `medium_airport` (public domain; `pipeline/data/airports.csv`,
  gitignored, download URL in `fit_model.py`). Stored with the airport name in
  `backend/artifacts/regions.json`. Caveat: "medium" includes restricted
  fields (Death Valley's nearest is Desert Rock, on the Nevada Test Site), so
  check the named airport.
- **Curated values are mostly blank.** Only Dry Valleys has a cost tier and permit flag, so:
  - **A** is the airport term only, with no permit factor, unless permit is filled in.
  - **R** and **C** are blank (shown as "-").
  - **Early stage** sorts by C. When C is blank for any passing patch it falls back to F and says so.
  - **Filters** on cost or season exclude regions with blank values once the filter is moved off its default.
  - **Pareto** uses only the scores known for every patch (currently F and A).

  These rules live in `backend/scoring.py`. Filling in `regions.csv` and rerunning
  `fit_model.py` turns the real scores on.

# Discovering new analogues (added after M6)

The main search only ranks patches inside the 22 curated regions, so it can
only return known analogue sites. Discover widens the net:

1. `pipeline/explore_corpus.py` stage 1 reads every ESA WorldCover 2021 v200
   tile (2651 tiles, Planetary Computer `esa-worldcover`, asset `map`) at its
   1/64 overview (~0.5 km samples). For each 0.25 deg cell it computes the
   land share and the bare share (class 60 "bare / sparse vegetation" +
   class 100 "moss and lichen"). Class 0 is nodata (sea outside coastlines)
   and 80 is water. WorldCover stops at 60S, so Antarctica is never explored.
2. Stage 2 keeps cells >= 95% land and >= 80% bare and drops cells within
   1 deg of a curated region. It spreads the sample (at most 2 cells per
   5 deg block, cap 1500) so the Sahara doesn't dominate, then reads
   Copernicus patches with the same QC as M1.
3. `fit_model.py` featurises them into `backend/artifacts/explore.npz` and
   labels each with its nearest large/medium airport.
4. `POST /api/discover` scores known and new patches together, so F is
   calibrated on the same pool, and returns only the new ones. The message
   says how many beat the best known analogue.

Limits: new candidates have no curated field season, cost, permit or
landform kind. "Bare" in WorldCover can include active dune fields, salt
crusts and military or protected land. The novelty thresholds still come
from the curated corpus.

Run 2026-11-15: 2651 WorldCover tiles read, 0 failed (145 s). 29,959 of
381,744 cells qualify; 671 near curated regions removed; 312 occupied 5 deg
blocks give 593 candidates. Copernicus reads: 553 kept, 38 skipped
(sea/nodata), 2 failed (333 s).

`/api/discover`, mobility, early stage, about 35 ms locally:

| target | best known (F) | best new (F) | new patches beating best known |
| --- | --- | --- | --- |
| marius_hills | pinacate_07 (0.937) | new_0004, Patagonia near El Bolsón AR (0.948) | 4 |
| taurus_littrow | dry_valleys_08 (0.988) | new_0246, near Las Vegas US (0.875) | 0 |
| tycho_rim | bonneville_04 (0.985) | new_0033, near Salta AR (0.933) | 0 |
