from __future__ import annotations
import math
import json
from pathlib import Path

import cadquery as cq
import trimesh

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '03_build' / 'v003'
BUILD.mkdir(parents=True, exist_ok=True)

# Canonical dimensions, millimetres
CANOPY_W = 45.0
CANOPY_HALF = CANOPY_W / 2.0
CANOPY_TOP = 20.6
CANOPY_TIP_Y = 1.0
CANOPY_RX = 24.7
CANOPY_RY = 23.0
CANOPY_RZ = 5.55
CANOPY_CY = 7.6
CANOPY_CZ = 0.85
SHAFT_R = 1.65
HANDLE_R = 1.90
LOOP_MAJOR_R = 3.15
LOOP_MINOR_R = 1.05
LOOP_ID = 2.0 * (LOOP_MAJOR_R - LOOP_MINOR_R)
TEXT_RAISE = 0.95

DARK = '#29485F'
CREAM = '#F2E6C9'
RED = '#C44A3D'


def canopy_points(n_top: int = 120, scallops: int = 6, n_scallop: int = 18):
    pts = []
    for i in range(n_top + 1):
        x = -CANOPY_HALF + CANOPY_W * i / n_top
        y = CANOPY_TIP_Y + (CANOPY_TOP - CANOPY_TIP_Y) * math.sqrt(max(0.0, 1.0 - (x / CANOPY_HALF) ** 2))
        pts.append((x, y))
    panel = CANOPY_W / scallops
    for s in range(scallops):
        x0 = CANOPY_HALF - s * panel
        x1 = CANOPY_HALF - (s + 1) * panel
        for j in range(1, n_scallop + 1):
            t = j / n_scallop
            x = x0 + (x1 - x0) * t
            y = CANOPY_TIP_Y + 3.0 * math.sin(math.pi * t)
            pts.append((x, y))
    return pts


def prism_from_polygon(points, z0, z1):
    return cq.Workplane('XY').polyline(points).close().extrude(z1-z0).translate((0,0,z0)).val()


def ellipsoid(rx, ry, rz, cy=0.0, cz=0.0):
    sphere = cq.Solid.makeSphere(1.0, angleDegrees1=-90, angleDegrees2=90)
    m = cq.Matrix([
        [rx, 0, 0, 0],
        [0, ry, 0, cy],
        [0, 0, rz, cz],
        [0, 0, 0, 1],
    ])
    return sphere.transformGeometry(m)


def cylinder_between(a, b, r):
    ax, ay, az = a; bx, by, bz = b
    vx, vy, vz = bx-ax, by-ay, bz-az
    length = math.sqrt(vx*vx + vy*vy + vz*vz)
    if length <= 1e-9:
        return cq.Solid.makeSphere(r, cq.Vector(ax,ay,az), angleDegrees1=-90, angleDegrees2=90)
    return cq.Solid.makeCylinder(r, length, cq.Vector(ax,ay,az), cq.Vector(vx,vy,vz))


def tube_along(points, radius):
    pieces = []
    for a,b in zip(points, points[1:]):
        pieces.append(cylinder_between(a,b,radius))
    for p in points[1:-1]:
        pieces.append(cq.Solid.makeSphere(radius*1.01, cq.Vector(*p), angleDegrees1=-90, angleDegrees2=90))
    out = pieces[0]
    for s in pieces[1:]:
        out = out.fuse(s)
    return out.clean()


def canopy_surface_z(x, y, front=True):
    q = 1.0 - (x/CANOPY_RX)**2 - ((y-CANOPY_CY)/CANOPY_RY)**2
    if q <= 0:
        return CANOPY_CZ
    dz = CANOPY_RZ * math.sqrt(q)
    return CANOPY_CZ + (dz if front else -dz)


def build_canopy():
    silhouette = prism_from_polygon(canopy_points(), -10.0, 10.0)
    lens = ellipsoid(CANOPY_RX, CANOPY_RY, CANOPY_RZ, CANOPY_CY, CANOPY_CZ).intersect(silhouette)

    for front, sign in ((True,1.0),(False,-1.0)):
        for xe in (-15.0,-7.5,0.0,7.5,15.0):
            pts=[]
            for i in range(8):
                t=i/7.0
                x=xe*(t**1.05)
                y=19.2 + (2.35-19.2)*t
                z=canopy_surface_z(x,y,front) + sign*0.18
                pts.append((x,y,z))
            segs=[]
            for a,b in zip(pts,pts[1:]):
                midy=(a[1]+b[1])/2.0
                if (not front) or midy>17.1 or midy<5.0:
                    segs.append(cylinder_between(a,b,0.43))
            if segs:
                rib=segs[0]
                for s in segs[1:]:
                    rib=rib.fuse(s)
                lens=lens.fuse(rib)
    return lens.clean()


def build_shaft_and_handle():
    shaft = cq.Solid.makeCylinder(SHAFT_R, 20.0, cq.Vector(0,1.5,0), cq.Vector(0,-1,0))
    pts=[(0.0,-18.0,0.0)]
    cx, cy, r = 4.25, -22.0, 5.25
    for deg in range(145, 383, 9):
        a=math.radians(deg)
        pts.append((cx+r*math.cos(a), cy+r*math.sin(a), 0.0))
    handle=tube_along(pts,HANDLE_R)
    return shaft.fuse(handle).clean()


def build_top_loop():
    torus = cq.Solid.makeTorus(LOOP_MAJOR_R, LOOP_MINOR_R, cq.Vector(0,24.15,0), cq.Vector(0,0,1))
    neck_pts=[(0.0,19.0,0.0),(0.0,21.4,0.0)]
    neck=tube_along(neck_pts,1.55)
    return torus.fuse(neck).clean()


def rounded_rect(w,h,r,z0,depth,center=(0,0)):
    x,y=center
    wp=cq.Workplane('XY').box(w,h,depth).translate((x,y,z0+depth/2.0))
    if r>0:
        wp=wp.edges('|Z').fillet(r)
    return wp.val()


def build_text_parts():
    raw = cq.Workplane('XY').text(
        'Schietwetter', 6.20, TEXT_RAISE,
        font='DejaVu Sans Condensed', kind='bold', halign='center', valign='center', combine=False
    ).val()
    solids = list(raw.Solids())
    i_dot, i_stem = solids[3], solids[4]
    bd=i_dot.BoundingBox(); bs=i_stem.BoundingBox()
    ix=((bd.xmin+bd.xmax)+(bs.xmin+bs.xmax))/4.0
    stem = cq.Workplane('XY').box(0.95, 3.55, TEXT_RAISE).translate((ix, -0.42, TEXT_RAISE/2.0)).val()
    neck = cq.Workplane('XY').box(0.62, 0.75, TEXT_RAISE).translate((ix, 1.46, TEXT_RAISE/2.0)).val()
    dot = cq.Workplane('XY').center(ix, 2.08).circle(0.60).extrude(TEXT_RAISE).val()
    i_shape = stem.fuse(neck).fuse(dot).clean()
    glyphs = [solids[0], solids[1], solids[2], i_shape] + solids[5:]
    chars = list('Schietwetter')
    assert len(glyphs) == len(chars) == 12

    out=[]
    y_offset=8.2
    for idx,(ch,glyph) in enumerate(zip(chars,glyphs),start=1):
        bb=glyph.BoundingBox()
        cx=(bb.xmin+bb.xmax)/2.0
        cy=(bb.ymin+bb.ymax)/2.0
        world_y=cy+y_offset
        q=max(1e-6, 1.0-(cx/CANOPY_RX)**2-((world_y-CANOPY_CY)/CANOPY_RY)**2)
        nx=cx/(CANOPY_RX*CANOPY_RX)
        nz=math.sqrt(q)/CANOPY_RZ
        angle=math.degrees(math.atan2(nx,nz))
        rotated=glyph.rotate((cx,cy,0),(cx,cy+1,0),angle)
        rzmin=rotated.BoundingBox().zmin
        penetration=0.55 if idx in (1,12) else 0.38
        target_base=canopy_surface_z(cx,world_y,True)-penetration
        placed=rotated.translate((0,y_offset,target_base-rzmin)).clean()
        out.append((f'schietwetter_text_{idx:02d}_{ch}', placed))
    return out


def build_hamburg_mark():
    z0=5.95
    depth=1.0
    wall=rounded_rect(11.2,2.2,0.32,z0,depth,center=(0,14.05))
    parts=[wall]
    for x,h,w in [(-3.45,3.0,2.1),(0.0,3.9,2.3),(3.45,3.0,2.1)]:
        cy=15.45+(h-3.0)/2.0
        tower=rounded_rect(w,h,0.26,z0,depth,center=(x,cy))
        roof_y=cy+h/2.0
        roof=cq.Workplane('XY').polyline([(x-w*0.62,roof_y),(x,roof_y+0.78),(x+w*0.62,roof_y)]).close().extrude(depth).translate((0,0,z0)).val()
        parts.extend([tower,roof])
    mark=parts[0]
    for p in parts[1:]:
        mark=mark.fuse(p)
    gate_rect=cq.Workplane('XY').box(1.30,0.92,depth+1.0,centered=(True,True,False)).translate((0,13.50,z0-0.5)).val()
    gate_round=cq.Workplane('XY').center(0,13.95).circle(0.65).extrude(depth+1.0).translate((0,0,z0-0.5)).val()
    return mark.cut(gate_rect.fuse(gate_round)).clean()


def build_main_body():
    body=build_canopy()
    body=body.fuse(build_shaft_and_handle())
    body=body.fuse(build_top_loop())
    return body.clean()


def export_shape(shape,path):
    cq.exporters.export(shape,str(path),tolerance=0.012,angularTolerance=0.12)
    mesh=trimesh.load_mesh(path,process=False)
    mesh.merge_vertices(merge_tex=True,merge_norm=True)
    mesh.update_faces(mesh.nondegenerate_faces(height=1e-8))
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals(multibody=False)
    path.write_bytes(mesh.export(file_type='stl'))


def main():
    main_body=build_main_body()
    text_parts=build_text_parts()
    mark=build_hamburg_mark()

    export_shape(main_body, BUILD/'schietwetter_umbrella_keychain_v003_umbrella_body.stl')
    for name,shape in text_parts:
        export_shape(shape, BUILD/f'{name}.stl')
    export_shape(mark, BUILD/'schietwetter_umbrella_keychain_v003_hamburg_mark.stl')

    assembly=cq.Compound.makeCompound([main_body,*[shape for _,shape in text_parts],mark])
    cq.exporters.export(assembly,str(BUILD/'schietwetter_umbrella_keychain_v003_exchange.step'))

    bodies=[
        {'name':'umbrella_body','path':'03_build/v003/schietwetter_umbrella_keychain_v003_umbrella_body.stl','color':DARK,'transform':[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]},
    ]
    for name,_ in text_parts:
        bodies.append({'name':name,'path':f'03_build/v003/{name}.stl','color':CREAM,'transform':[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]})
    bodies.append({'name':'hamburg_mark','path':'03_build/v003/schietwetter_umbrella_keychain_v003_hamburg_mark.stl','color':RED,'transform':[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]})

    manifest={
        'schema_version':1,
        'model':'schietwetter_umbrella_keychain',
        'version':'v003',
        'units':'mm',
        'canonical_source':'02_source/schietwetter_umbrella_keychain_v003_source.py',
        'bodies':bodies,
        'design_notes':{
            'canopy_width_mm':CANOPY_W,
            'loop_hole_mm':LOOP_ID,
            'full_3d_canopy':True,
            'flat_back':False,
            'round_shaft_and_handle':True,
            'wrapped_lettering':True,
            'fine_decor_omitted':['small seagulls','thin waves','micro-icons']
        }
    }
    (ROOT/'02_source'/'source-manifest-v003.json').write_text(json.dumps(manifest,indent=2),encoding='utf-8')

    bb=main_body.BoundingBox()
    print('main',bb.xlen,bb.ylen,bb.zlen,'solids',len(main_body.Solids()))
    print('text_parts',len(text_parts))
    print('loop_hole',LOOP_ID)

if __name__=='__main__':
    main()
