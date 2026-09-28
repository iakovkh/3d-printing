# Staunton queen keychain v001 — reopened candidate QA

- Candidate ID: `E6324A02`
- SHA-256: `e6324a026169c36e19f9691c8237c4fc7611b26070420a0122a24adbd5e2844e`
- Bounds: `22.500 × 22.500 × 50.000 mm`
- Body count: `1`
- Connected components: `1`
- Watertight: `True`
- Winding consistent: `True`
- Euler number: `2`
- Degenerate faces: `0`
- Base diameter: `22.500 mm`
- Ring hole: `0.000 mm`
- Finial outer diameter: `0.000 mm`
- Minimum hole ligament: `0.000 mm`
- Crown peaks: `8`
- Base-plane error: `0.0000 mm`
- 3MF XML: `274716` vertices / `549428` triangles

## Blockers

- could not identify the ring hole in reopened geometry: expected inner and outer section rings, got medians [3.9976258174076023]

## Warnings

- Horizontal 3.2 mm bore creates a short bridge; inspect the sliced roof and add local support only if needed
- Crown valleys and tooth undersides may create local overhangs; inspect layers in Anycubic Slicer Next
- Slicer profile, seam, material flow, print time, and support placement are not validated by geometry QA
