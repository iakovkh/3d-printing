# v004 feasibility attempt — no candidate produced

Status: FAILED_BEFORE_GEOMETRY  
Version namespace: v004  
Date: 2026-09-29

## Purpose

The v004 attempt was intended to replace the rejected CAD-style v001-v003 line with an organic/image-to-3D starting point that could preserve the approved souvenir concept much more faithfully.

## What was tried

1. The approved concept image was selected as a visual reference only.
2. An image-to-3D route was attempted through the connected to3D service.
3. The service failed with `Generation Failed — Internal error`.
4. A second image-to-3D route was evaluated through fal.ai. The recommended endpoint was `fal-ai/hunyuan-3d/v3.1/pro/image-to-3d`.
5. The fal.ai upload step returned HTTP 403 with `balance_exhausted` before any generation job could start.

## Result

No usable mesh, GLB, STL, Blender source or candidate 3MF was created.

Therefore:
- there is no v004 candidate ID;
- v004 is not READY_FOR_REVIEW;
- no preview may be presented as a render from v004 geometry;
- no release may be created;
- the approved concept remains a concept only.

## Decision

Do not continue with simplified CAD geometry. The next retained implementation attempt must use manual organic modeling in Blender, following `02_source/schietwetter_umbrella_keychain_blender_modeling_spec.md`.

The next actual candidate must receive a new immutable version number after real Blender geometry exists. Do not reuse a failed candidate namespace for a different exported mesh.
