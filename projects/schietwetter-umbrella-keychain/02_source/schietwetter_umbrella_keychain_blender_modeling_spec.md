# Blender modeling specification — Schietwetter umbrella keychain

Status: APPROVED HANDOFF BASIS  
Model class: ORGANIC / HYBRID souvenir keychain  
Canonical modeling tool: Blender  
Target printer: Anycubic Kobra S1 Combo  
Target slicer: Anycubic Slicer Next  
Units: mm  
Default material: PLA  
Default nozzle: 0.4 mm

## 1. Goal

Create a genuinely attractive Hamburg souvenir keychain that preserves the character of the approved concept while remaining printable at a 45 mm canopy width.

The target is not a literal reconstruction of every AI-generated micro-detail. The target is the same product character:
- compact premium souvenir;
- rounded, friendly, toy-like umbrella proportions;
- deep sculpted canopy;
- polished ribs and end caps;
- smooth cylindrical shaft and J-handle;
- top keyring eyelet integrated into a small crown;
- large readable `Schietwetter` wordmark following the canopy;
- simplified Hamburg three-tower mark above the wordmark;
- dark blue / cream / red palette.

The concept image is an artistic reference only and must always be labeled:
`КОНЦЕПТ — НЕ РЕНДЕР 3D-МОДЕЛИ`

## 2. Mandatory visual contract

The final reopened 3MF must satisfy all of the following in technical proof views:

1. The object immediately reads as a miniature umbrella from front, side, rear and isometric views.
2. The canopy must be a deep dome, not a plate with surface embossing.
3. The silhouette must be soft and rounded. No large planar badge-like areas are allowed on the canopy.
4. Six primary canopy panels are preferred. The panel valleys and ribs must produce visible three-dimensional structure without becoming thin decorative wires.
5. The lower edge must use six broad scallops. Each rib terminates in a rounded end cap.
6. The shaft and J-handle must be cylindrical/rounded and visually substantial.
7. The top eyelet must grow organically from a crown at the canopy apex rather than look glued onto a plate.
8. `Schietwetter` must follow the dome curvature and look integrated into the product. A rectangular or flat backing plaque is prohibited.
9. The Hamburg mark must be deliberately simplified and balanced with the wordmark.
10. No micro-decoration is required. Beauty and proportion take priority over quantity of icons.

## 3. Target dimensions

These are modeling targets. Exact final dimensions are verified after candidate 3MF round-trip.

- canopy maximum width X: 45.0 mm
- canopy maximum depth Z: target 15.0-17.0 mm
- canopy visible height from scallop baseline to crown: target 20.0-22.0 mm
- overall keychain height including handle and eyelet: target 58-62 mm
- shaft diameter: 3.4-4.0 mm
- J-handle section diameter: 4.0-4.6 mm
- J-handle outside width: target 12-14 mm
- eyelet hole diameter: 4.0-4.2 mm
- eyelet section thickness: minimum 2.0 mm around the hole
- structural canopy shell / solid thickness where applicable: minimum 1.6 mm, target 1.8-2.2 mm
- rib proud height: target 0.8-1.1 mm
- rib width: minimum 1.0 mm
- rounded end-cap diameter: target 2.0-2.6 mm

A slightly thicker or deeper object is acceptable if it is visibly better and still comfortable as a keychain. Do not flatten the design to make support-free printing easier.

## 4. Canopy modeling method

Preferred Blender method:
1. Create one clean six-segment canopy surface using radial symmetry.
2. Sculpt/profile one panel with smooth convex curvature.
3. Use radial duplication or a six-fold construction so all panel boundaries are controlled and regular.
4. Shape the scalloped bottom edge as part of the primary surface, not by attaching a flat decorative skirt.
5. Give the canopy real thickness using Solidify or an equivalent controlled shell workflow.
6. Add Subdivision Surface for smoothness, retaining enough support loops to keep the scallops and crown crisp.
7. Model ribs as rounded integrated geometry following panel boundaries.
8. Model rounded tips/end caps as part of the dark blue structural body.
9. Model the underside intentionally. It must look like the underside of an umbrella, not an accidental backface.

Avoid voxel remesh settings that destroy the controlled scallop edge or make the dome lumpy.

## 5. Shaft, handle and eyelet

### Shaft
- centered under the crown;
- circular cross-section;
- smooth transition into the underside of the canopy;
- no wafer-thin connection.

### J-handle
- use a Bezier curve with bevel or an equivalent smooth swept profile;
- section diameter 4.0-4.6 mm;
- hook radius large enough to look elegant, not cramped;
- blend the upper handle transition into the shaft with a small collar if visually useful.

### Eyelet
- round or softly oval;
- hole 4.0-4.2 mm;
- create a small crown/base that transitions into the dome;
- minimum wall around the hole 2.0 mm;
- no printed metal ring geometry.

## 6. Wordmark

Exact text: `Schietwetter`

The wordmark is the principal graphic element.

Requirements:
- friendly tourist/souvenir character, visually close to the approved concept;
- use a rounded semiscript/brush-like shape, not a generic engineering sans font;
- convert text to curves/mesh before finalization;
- manually thicken thin strokes;
- target word width: approximately 33-37 mm;
- target capital height: approximately 5.5-6.5 mm;
- minimum stroke width after all deformation: 0.9 mm;
- relief above canopy: 0.7-0.9 mm;
- base of the wordmark follows the curved canopy via Shrinkwrap or direct surface placement;
- embed/contact the cream body into the canopy surface by approximately 0.20-0.35 mm for a reliable shared interface;
- keep the wordmark as one connected cream body if possible. Natural letter connections are preferred. A subtle hidden connector may be used only where necessary.

No rectangular plaque behind the word.

## 7. Hamburg mark

Use a simplified three-tower Hamburg-style castle motif.

Target:
- width 9-11 mm;
- relief 0.7-0.9 mm;
- red body;
- minimum feature width 0.8 mm;
- one arch/gate may be retained if it remains printable;
- no tiny stars, windows or spires are required;
- place above the wordmark with clear breathing room.

A single broad cream wave under the castle is optional only if it remains visually clean and passes the minimum feature limits.

## 8. Deliberately omitted details

Do not promise or model these by default:
- tiny gulls;
- multiple thin waves;
- micro raindrops;
- small anchors;
- micro lettering;
- fine skyline details;
- texture-only decorative noise.

One or two large raindrops may be considered later only if the basic composition already looks excellent and the parts remain printable.

## 9. Color / part structure

Preferred 3MF part structure:
- `umbrella_body` — dark navy blue
- `schietwetter_wordmark` — cream / warm white
- `hamburg_mark` — red
- optional `simple_wave` — cream, only if retained

Each color part must be named and preserved independently through the 3MF round-trip.

The printed result is one assembled object. Color bodies must meet the canopy cleanly without floating geometry.

## 10. Blender source rules

The canonical source is one versioned `.blend` file.

Recommended collections:
- `REF_CONCEPT_DO_NOT_EXPORT`
- `BODY_DARK_BLUE`
- `TEXT_CREAM`
- `MARK_RED`
- `QA_HELPERS_DO_NOT_EXPORT`

Keep the concept reference image in a non-export collection and mark it clearly as concept-only.

Use real dimensions in millimetres. Before export:
- apply object scale;
- verify normals;
- remove hidden accidental fragments;
- apply only the modifiers required for the exported geometry;
- retain an editable source copy in the same versioned `.blend`.

All geometry changes must originate in the canonical Blender source.

## 11. FDM design constraints

For 0.4 mm nozzle PLA:
- structural thickness below 1.6 mm is a BLOCKER unless specifically justified;
- decorative strokes below 0.8 mm are a BLOCKER;
- preferred decorative strokes are 0.9 mm or wider;
- avoid unsupported needle-like details;
- avoid deep narrow slots that cannot be resolved by the nozzle;
- eyelet and handle strength take priority over exact visual thinness.

Supports are allowed. Do not flatten the model to avoid them.

## 12. Required export cycle

For the first real Blender implementation after this handoff:

1. Create a new immutable version number.
2. Save the versioned canonical `.blend`.
3. Export named color bodies to STL and, where useful, a combined STEP/mesh exchange artifact.
4. Build versioned `candidate.3mf`.
5. Reopen candidate independently.
6. Measure X/Y/Z and eyelet hole after reopening.
7. Verify body names, count, colors and transforms.
8. Run watertight/manifold/degenerate/normal/component QA.
9. Run minimum-thickness and self-intersection checks with a capable tool before release. These checks may not be silently left as `NOT_VERIFIED` for the manual Blender candidate.
10. Render front, back, side, top, isometric, dimensions and parts/colors only from reopened candidate geometry.
11. Compare the technical views against the mandatory visual contract.
12. If the object still reads as a crude CAD charm, reject the version internally and continue modeling. Do not ask the user to approve it.

## 13. Visual acceptance gate

A version is not acceptable merely because it is watertight.

Before asking for user approval, all answers below must be YES:
- Does the isometric view immediately resemble the approved premium umbrella concept?
- Does the side view clearly show a deep sculpted dome?
- Is the back intentionally modeled rather than flat?
- Do the six scallops and ribs look coherent and smooth?
- Do the shaft, handle and eyelet look rounded and proportionate?
- Is `Schietwetter` large, elegant and naturally wrapped onto the canopy?
- Is the Hamburg mark simple, recognizable and balanced?
- Is there no flat plaque under the wordmark?
- Is there no clutter of tiny unprintable decoration?
- Would the object still look attractive if rendered as a single neutral material?

If any answer is NO, the candidate stays in GEOMETRY_DRAFT.

## 14. Release gate

Release is allowed only after:
- user approves exact version and SHA-derived short ID;
- released 3MF is a byte-identical copy of the approved candidate;
- released file reopens successfully;
- SHA-256 matches the approved candidate;
- all required visual proof images correspond to the same reopened geometry;
- no BLOCKER remains.
