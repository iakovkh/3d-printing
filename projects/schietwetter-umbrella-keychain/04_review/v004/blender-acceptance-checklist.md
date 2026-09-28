# Blender candidate acceptance checklist

Use this checklist for the first manual Blender candidate after the failed v004 feasibility attempt.

## Visual

- [ ] 45 mm canopy reads as a premium miniature umbrella, not a badge
- [ ] dome depth target 15-17 mm
- [ ] modeled underside/back, no flat rear plate
- [ ] six clean broad scallops
- [ ] six-panel sculptural structure
- [ ] rounded ribs and rounded end caps
- [ ] cylindrical shaft
- [ ] elegant round J-handle
- [ ] organic top crown and 4.0-4.2 mm eyelet
- [ ] Schietwetter is the dominant graphic
- [ ] wordmark follows dome curvature
- [ ] no flat wordmark plaque
- [ ] Hamburg three-tower mark is simplified and balanced
- [ ] no unnecessary micro-decoration
- [ ] neutral-material render would still look attractive

## Geometry after candidate.3mf reopen

- [ ] units = millimetres
- [ ] canopy width = 45.0 mm ± 0.2 mm
- [ ] overall size plausible for keychain
- [ ] eyelet hole = 4.0-4.2 mm within tolerance
- [ ] expected named color bodies preserved
- [ ] transforms preserved
- [ ] every exported body watertight
- [ ] manifold geometry
- [ ] consistent normals
- [ ] no degenerate faces
- [ ] no accidental loose fragments
- [ ] connected components match design intent
- [ ] self-intersections VERIFIED
- [ ] minimum wall thickness VERIFIED
- [ ] structural thickness >= 1.6 mm
- [ ] decorative stroke width >= 0.8 mm, target >= 0.9 mm

## Printing

- [ ] print orientation documented
- [ ] support strategy documented
- [ ] support contact does not destroy the wordmark or keyring eyelet
- [ ] no hidden unsupported needle-like geometry
- [ ] user will perform final layer preview in Anycubic Slicer Next

## Traceability

- [ ] canonical Blender source version matches candidate version
- [ ] candidate SHA-256 recorded
- [ ] all proof images contain same version and short ID
- [ ] proof images generated only from reopened candidate
- [ ] no release before exact user approval
