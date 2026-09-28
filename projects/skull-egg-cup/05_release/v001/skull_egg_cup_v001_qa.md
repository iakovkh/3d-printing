# Skull egg cup v001 — reopened candidate QA

- Candidate ID: `1C8BB486`
- SHA-256: `1c8bb4862b0d15b6e86022b353e9049e50a7d7c0389344515c8e35c3aa919d06`
- Bounds: `77.952 × 87.916 × 74.000 mm`
- Body count: `1`
- Connected components: `1`
- Watertight: `True`
- Winding consistent: `True`
- Euler number: `-46`
- Degenerate faces: `0`
- Opening: `41.988 mm`
- Bowl depth: `22.000 mm`
- Minimum measured functional wall: `4.523 mm`
- Base-plane error: `0.0000 mm`
- 3MF XML: `325006` vertices / `650104` triangles

## Section wall samples

- Z `73.400` mm: `4.523` mm
- Z `72.000` mm: `4.789` mm
- Z `70.000` mm: `5.987` mm

## Blockers

- None

## Warnings

- PLA temperature risk accepted by user
- Anatomical undercuts and dental detail may require slicer supports
- Hand wash only; geometry file contains no validated food-contact or dishwasher certification
- Intentional anatomical passages yield Euler number -46 (genus 24); accepted because the mesh is one connected watertight manifold

## Slicer verification

- Anycubic Slicer Next reproduced the expected dimensions: `77.9524 × 87.9156 × 74 mm`.
- The slicer detected floating layer regions with supports disabled; independent geometry analysis confirmed these are anatomical overhangs rather than disconnected mesh fragments.
- The user's sliced preview at `0.20 mm` layer height shows organic/tree supports under the cranial base, cheekbones, jaw and dental overhangs, with the egg bowl and upper rim unobstructed.
- Supports are therefore required in the approved upright orientation. Minor contact texture on supported lower surfaces remains a normal FDM risk, not a release blocker.
