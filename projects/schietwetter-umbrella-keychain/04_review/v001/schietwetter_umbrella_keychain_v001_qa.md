# QA — Schietwetter Umbrella Keychain v001

Candidate ID: **62091427**  
SHA-256: `620914271cae8ecd6ef803721fc31b83198ae7f6e106198e50a3ddee09aa8f57`

## Reopened candidate

- Overall X/Y/Z: 45.044 × 5.747 × 56.641 mm
- Bodies: 7
- Keyring aperture: 4.100 × 4.100 mm
- Flat print back: Y = +1.000 mm

## Critical structural checks

- Canopy perimeter core: 2.20 mm
- Shaft diameter: 3.50 mm
- Handle diameter: 3.70 mm
- Loop radial wall: 2.05 mm

## Findings

- **INFO SELF_INTERSECTION_LIMIT**: No independent exhaustive triangle-pair self-intersection engine was available; structural OpenSCAD CGAL export reported Simple=yes and reopened meshes are watertight/winding-consistent.
- **INFO PRINT_ORIENTATION**: Lay the flat back on the build plate. In this orientation the loop hole is vertical and the domed front builds upward.
- **INFO SUPPORTS**: Designed for back-face-down printing without routine supports; confirm layer preview in Anycubic Slicer Next.
- **WARNING TEXT_DETAIL**: The 45 mm format makes Schietwetter the limiting detail. The wordmark is boldened by a 0.12 mm 2D offset, but verify the first sliced-layer preview for complete glyph strokes with the 0.4 mm nozzle.

## Body topology

- `umbrella_body`: watertight=True, components=1, winding=True, Δvolume=0.000015 mm³
- `schietwetter_text_01`: watertight=True, components=1, winding=True, Δvolume=0.000000 mm³
- `schietwetter_text_02`: watertight=True, components=1, winding=True, Δvolume=0.000000 mm³
- `schietwetter_text_03`: watertight=True, components=1, winding=True, Δvolume=0.000000 mm³
- `schietwetter_text_04`: watertight=True, components=1, winding=True, Δvolume=0.000000 mm³
- `schietwetter_text_05`: watertight=True, components=1, winding=True, Δvolume=0.000000 mm³
- `hamburg_mark`: watertight=True, components=1, winding=True, Δvolume=0.000011 mm³

## Status

READY_FOR_REVIEW
