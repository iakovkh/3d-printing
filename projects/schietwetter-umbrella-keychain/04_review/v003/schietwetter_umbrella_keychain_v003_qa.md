# QA — Schietwetter Umbrella Keychain v003

Status: READY_FOR_REVIEW  
Candidate ID: `0A39D26B`  
SHA-256: `0a39d26b7071994f7aab816c04be3af6bcd431f82244e20134415af226ff0b8b`

## Corrected 3D requirement

v002 was rejected by the user because its flat rear face made the keychain read as a relief rather than a true 3D umbrella. v003 removes the flat backplate completely. The canopy is rounded on both sides; the shaft, J-handle and top eyelet have round cross-sections.

## Reopened candidate

- Units: mm
- Overall X/Y/Z: 45.000 × 57.517 × 12.347 mm
- Canopy width: 45.000 mm
- Main umbrella body depth: 12.276 mm
- Top eyelet hole: 4.201 mm measured from reopened mesh
- Bodies: 14
- Flat back: no

## Geometry checks

All 14 reopened bodies:
- watertight: VERIFIED
- connected components: exactly 1 per body
- winding consistent: VERIFIED
- degenerate faces: none

BLOCKER: 0

## Warnings

- `SUPPORT_RISK`: the true 3D shape intentionally has no flat back, so orientation/support work is expected in Anycubic Slicer Next.
- `MIN_WALL_GLOBAL_NOT_VERIFIED`: critical source dimensions were designed for a 0.4 mm nozzle, but a complete mesh-wide medial thickness scan is unavailable.
- `SELF_INTERSECTION_GLOBAL_NOT_VERIFIED`: reopened meshes are watertight and consistent, but a dedicated global self-intersection scan is unavailable.

## Traceability

Every review image for v003 is generated only from geometry independently reopened from the candidate 3MF. v003 is not released until the user explicitly approves version and ID.
