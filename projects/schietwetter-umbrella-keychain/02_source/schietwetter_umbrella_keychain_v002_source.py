from __future__ import annotations
import math
import json
from pathlib import Path
import cadquery as cq
import trimesh
from shapely.geometry import LineString

ROOT = Path(__file__).resolve().parents[1]
BUILD = ROOT / '03_build' / 'v002'
BUILD.mkdir(parents=True, exist_ok=True)

# Canonical dimensions, millimetres
CANOPY_W = 45.0
CANOPY_HALF = CANOPY_W / 2.0
CANOPY_TOP = 21.0
CANOPY_TIP_Y = 1.0
MAIN_BACK_Z = -2.2
MAIN_FRONT_Z = 2.2
ELLIPSOID_RX = 24.5
ELLIPSOID_RY = 22.0
ELLIPSOID_RZ = 4.0
ELLIPSOID_CY = 8.0
LOOP_OD = 8.8
LOOP_ID = 4.2
TEXT_RAISE = 0.8

DARK = '#29485F'
CREAM = '#F2E6C9'
RED = '#C44A3D'


def canopy_points(n_top: int = 96, scallops: int = 6, n_scallop: int = 14):
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
    wp = cq.Workplane('XY').polyline(points).close().extrude(z1-z0)
    return wp.translate((0, 0, z0)).val()


def rounded_rect(w, h, r, z0, depth, center=(0,0)):
    x, y = center
    wp = cq.Workplane('XY').box(w, h, depth).translate((x, y, z0 + depth/2.0))
    if r > 0:
        wp = wp.edges('|Z').fillet(r)
    return wp.val()


def extrude_polygon(poly, z0, depth):
    coords = list(poly.exterior.coords)[:-1]
    shape = cq.Workplane('XY').polyline(coords).close().extrude(depth).translate((0,0,z0)).val()
    for interior in poly.interiors:
        hole = cq.Workplane('XY').polyline(list(interior.coords)[:-1]).close().extrude(depth+1.0).translate((0,0,z0-0.5)).val()
        shape = shape.cut(hole)
    return shape


def build_j_handle():
    pts = [(0.0, 2.0), (0.0, -17.4)]
    cx, cy, radius = 4.0, -22.0, 5.15
    for deg in range(140, 381, 8):
        a = math.radians(deg)
        pts.append((cx + radius*math.cos(a), cy + radius*math.sin(a)))
    poly = LineString(pts).buffer(1.90, quad_segs=10, cap_style='round', join_style='round')
    return extrude_polygon(poly, MAIN_BACK_Z, 4.8)


def ellipsoid():
    sphere = cq.Solid.makeSphere(1.0)
    m = cq.Matrix([
        [ELLIPSOID_RX, 0, 0, 0],
        [0, ELLIPSOID_RY, 0, ELLIPSOID_CY],
        [0, 0, ELLIPSOID_RZ, 0],
        [0, 0, 0, 1],
    ])
    return sphere.transformGeometry(m)


def cylinder_between(a, b, r):
    ax, ay, az = a; bx, by, bz = b
    vx, vy, vz = bx-ax, by-ay, bz-az
    length = math.sqrt(vx*vx+vy*vy+vz*vz)
    return cq.Solid.makeCylinder(r, length, cq.Vector(ax,ay,az), cq.Vector(vx,vy,vz))


def surface_z(x, y):
    q = 1.0 - (x/ELLIPSOID_RX)**2 - ((y-ELLIPSOID_CY)/ELLIPSOID_RY)**2
    return ELLIPSOID_RZ * math.sqrt(max(0.0, q))


def rib_curve(x_end, y_end, radius=0.47):
    points = []
    for i in range(11):
        t = i / 10.0
        x = x_end * (t ** 1.08)
        y = 19.6 + (y_end - 19.6) * t
        z = surface_z(x, y) + 0.22
        points.append((x,y,z))
    solids = []
    protected_low, protected_high = 5.2, 18.2
    for a,b in zip(points, points[1:]):
        if (a[1] > protected_high and b[1] > protected_high) or (a[1] < protected_low and b[1] < protected_low):
            solids.append(cylinder_between(a,b,radius))
    for p in points[1:-1]:
        if p[1] > protected_high or p[1] < protected_low:
            solids.append(cq.Solid.makeSphere(radius, cq.Vector(*p)))
    out = solids[0]
    for s in solids[1:]:
        out = out.fuse(s)
    return out


def build_main_body():
    silhouette = prism_from_polygon(canopy_points(), -5.0, 5.0)
    dome = ellipsoid().intersect(silhouette)
    back_cut = cq.Workplane('XY').box(80, 100, 6.2, centered=(True, True, False)).translate((0, -8, MAIN_BACK_Z)).val()
    dome = dome.intersect(back_cut)
    backplate = prism_from_polygon(canopy_points(), MAIN_BACK_Z, MAIN_BACK_Z + 1.0)
    dome = dome.fuse(backplate)

    handle = build_j_handle()

    ro = LOOP_OD/2.0; ri = LOOP_ID/2.0
    loop_outer = cq.Workplane('XY').center(0,24.6).circle(ro).extrude(4.8).translate((0,0,MAIN_BACK_Z)).val()
    loop_inner = cq.Workplane('XY').center(0,24.6).circle(ri).extrude(6.0).translate((0,0,MAIN_BACK_Z-0.6)).val()
    loop = loop_outer.cut(loop_inner)
    neck = rounded_rect(4.6, 3.5, 1.1, MAIN_BACK_Z, 4.8, center=(0,21.1))

    text_pad = rounded_rect(39.0, 7.1, 1.5, 2.15, 1.45, center=(0,8.0))

    body = dome.fuse(handle).fuse(loop).fuse(neck).fuse(text_pad)

    for xe in (-15.0, -7.5, 0.0, 7.5, 15.0):
        panel = CANOPY_W/6.0
        u = (xe + CANOPY_HALF) / panel
        frac = u - math.floor(u)
        edge_y = CANOPY_TIP_Y + 3.0*math.sin(math.pi*frac)
        body = body.fuse(rib_curve(xe, edge_y + 0.5))

    return body


def build_text_body():
    text = cq.Workplane('XY').text(
        'Schietwetter', 6.7, TEXT_RAISE,
        font='Comic Neue', kind='bold', halign='center', valign='center', combine=False
    ).translate((0,8.1,3.55)).val()
    underline = rounded_rect(36.0, 0.90, 0.38, 3.55, TEXT_RAISE, center=(0,6.12))
    i_bridge = rounded_rect(0.90, 1.30, 0.22, 3.55, TEXT_RAISE, center=(-6.46, 9.10))
    return text.fuse(underline).fuse(i_bridge)


def build_hamburg_mark():
    z0 = 3.20
    depth = 0.95
    wall = rounded_rect(11.5, 2.3, 0.35, z0, depth, center=(0,14.15))
    parts = [wall]
    for x, h, w in [(-3.55,3.1,2.15),(0,4.0,2.35),(3.55,3.1,2.15)]:
        tower = rounded_rect(w, h, 0.28, z0, depth, center=(x,15.65 + (h-3.1)/2))
        roof_y = 15.65 + (h-3.1)/2 + h/2
        roof = cq.Workplane('XY').polyline([
            (x-w*0.62, roof_y),
            (x, roof_y+0.82),
            (x+w*0.62, roof_y),
        ]).close().extrude(depth).translate((0,0,z0)).val()
        parts += [tower, roof]
    mark = parts[0]
    for part in parts[1:]:
        mark = mark.fuse(part)
    gate_rect = cq.Workplane('XY').box(1.35, 1.0, depth+1.0, centered=(True, True, False)).translate((0,13.55,z0-0.5)).val()
    gate_round = cq.Workplane('XY').center(0,14.05).circle(0.675).extrude(depth+1.0).translate((0,0,z0-0.5)).val()
    return mark.cut(gate_rect.fuse(gate_round))


def clean(shape):
    return shape.clean()


def export_shape(shape, path):
    cq.exporters.export(shape, str(path), tolerance=0.015, angularTolerance=0.15)
    mesh = trimesh.load_mesh(path, process=False)
    mesh.merge_vertices(merge_tex=True, merge_norm=True)
    mesh.update_faces(mesh.nondegenerate_faces(height=1e-8))
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals(multibody=False)
    path.write_bytes(mesh.export(file_type='stl'))


def main():
    main_body = clean(build_main_body())
    text_body = clean(build_text_body())
    mark = clean(build_hamburg_mark())

    export_shape(main_body, BUILD/'schietwetter_umbrella_keychain_v002_umbrella_body.stl')
    export_shape(text_body, BUILD/'schietwetter_umbrella_keychain_v002_text_and_simple_decor.stl')
    export_shape(mark, BUILD/'schietwetter_umbrella_keychain_v002_hamburg_mark.stl')

    assembly = cq.Compound.makeCompound([main_body, text_body, mark])
    cq.exporters.export(assembly, str(BUILD/'schietwetter_umbrella_keychain_v002_exchange.step'))

    manifest = {
        'schema_version': 1,
        'model': 'schietwetter_umbrella_keychain',
        'version': 'v002',
        'units': 'mm',
        'canonical_source': '02_source/schietwetter_umbrella_keychain_v002_source.py',
        'bodies': [
            {'name':'umbrella_body','path':'03_build/v002/schietwetter_umbrella_keychain_v002_umbrella_body.stl','color':DARK,'transform':[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]},
            {'name':'text_and_simple_decor','path':'03_build/v002/schietwetter_umbrella_keychain_v002_text_and_simple_decor.stl','color':CREAM,'transform':[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]},
            {'name':'hamburg_mark','path':'03_build/v002/schietwetter_umbrella_keychain_v002_hamburg_mark.stl','color':RED,'transform':[1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]},
        ],
        'design_notes': {
            'canopy_width_mm': CANOPY_W,
            'loop_hole_mm': LOOP_ID,
            'flat_back': True,
            'fine_decor_omitted': ['small seagulls','thin waves','micro-icons'],
        }
    }
    (ROOT/'02_source'/'source-manifest.json').write_text(json.dumps(manifest, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
