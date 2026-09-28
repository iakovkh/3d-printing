# QA — Schietwetter Umbrella Keychain v002

Status: READY_FOR_REVIEW  
Candidate ID: `88216554`  
SHA-256: `88216554808f8d4c635b3b6e22fdffd38861329d0d047ec7664f0290de5b3a5d`

## Reopened candidate

- Units: mm
- Overall X/Y/Z: 45.000 × 58.043 × 6.856 mm
- Canopy width: 45.000 mm
- Top loop hole: 4.200 mm
- Bodies: 3
- Flat print back plane: z = -2.200 mm

## Geometry checks

| Body | Watertight | Connected components | Winding | Degenerate faces |
|---|---:|---:|---:|---:|
| umbrella_body | TRUE | 1 | TRUE | FALSE |
| text_and_simple_decor | TRUE | 1 | TRUE | FALSE |
| hamburg_mark | TRUE | 1 | TRUE | FALSE |

BLOCKER: 0

## Warnings

- `MIN_WALL_GLOBAL_NOT_VERIFIED`: critical designed features were dimensioned for 0.4 mm FDM printing, but a full mesh-wide medial thickness scan was not available in this environment.
- `SELF_INTERSECTION_GLOBAL_NOT_VERIFIED`: reopened meshes are watertight, single-component and winding-consistent, but a dedicated global mesh self-intersection scan was not available.

## Printing intent

The back is deliberately planar across the canopy, shaft, handle and loop. Intended orientation is back-down with colored text and Hamburg mark facing upward. This is a geometry recommendation only; final slicing and layer/support inspection remain in Anycubic Slicer Next.

## Traceability

All review images were generated from bodies independently reopened from `03_build/v002/schietwetter_umbrella_keychain_v002_candidate.3mf`. They are not concept renders.
