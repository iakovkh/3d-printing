// Schietwetter Umbrella Keychain v001
// Canonical source for project schietwetter-umbrella-keychain
// Units: mm
// Coordinate system: X = width, Y = depth, Z = height. Front = -Y.
// Export with: openscad -D 'part="body"' ... / 'text' / 'mark'

$fn = 32;
part = "assembly";

canopy_w = 45.22;
canopy_depth = 9.0;
canopy_h = 12.8;
body_blue = [0.10,0.20,0.34];
text_cream = [0.95,0.90,0.78];
mark_red = [0.75,0.12,0.10];

module ellipsoid(rx, ry, rz) {
    scale([rx, ry, rz]) sphere(r=1);
}

module capsule_between(p1, p2, r=1.0) {
    hull() {
        translate(p1) sphere(r=r);
        translate(p2) sphere(r=r);
    }
}

module scallop_cutter(xc) {
    translate([xc, 0, -0.7])
        scale([1.0, 1.0, 0.63])
            rotate([90,0,0]) cylinder(h=24, r=4.25, center=true);
}

module canopy_silhouette_2d() {
    difference() {
        intersection() {
            scale([canopy_w/2, canopy_h]) circle(r=1);
            translate([-30,0]) square([60,20]);
        }
        for (xc=[-18.75,-11.25,-3.75,3.75,11.25,18.75])
            translate([xc,-0.7]) scale([4.25,4.25*0.63]) circle(r=1);
    }
}

module canopy_backplate() {
    rotate([90,0,0])
        linear_extrude(height=2.40, center=true, convexity=10)
            canopy_silhouette_2d();
}

module canopy_core() {
    union() {
        difference() {
            intersection() {
                translate([0,0,0]) ellipsoid(canopy_w/2, canopy_depth/2, canopy_h);
                translate([-30,-10,0]) cube([60,20,20]);
            }
            for (xc=[-18.75,-11.25,-3.75,3.75,11.25,18.75])
                scallop_cutter(xc);
        }
        canopy_backplate();
    }
}

module handle_path() {
    pts = [
        [0.0,0,-30.0],
        [0.78,0,-32.9],
        [2.90,0,-35.02],
        [5.80,0,-35.80],
        [8.70,0,-35.02],
        [10.82,0,-32.9],
        [11.60,0,-30.0]
    ];
    for (i=[0:len(pts)-2]) capsule_between(pts[i], pts[i+1], 1.85);
}

module top_loop() {
    translate([0,0,14.9])
        rotate([90,0,0])
            rotate_extrude(convexity=10)
                translate([3.075,0,0]) circle(r=1.025);
}

module front_ribs() {
    apex = [0,-1.2,10.8];
    ribs = [
        [-15.0,-2.55,1.0],
        [-7.5,-3.55,0.8],
        [0.0,-4.05,0.7],
        [7.5,-3.55,0.8],
        [15.0,-2.55,1.0]
    ];
    for (p=ribs) capsule_between(apex, p, 0.70);
}

module umbrella_body_unclipped() {
    union() {
        canopy_core();
        translate([0,0,-30.0]) cylinder(h=31.5, r=1.75);
        handle_path();
        top_loop();
        front_ribs();
    }
}

module umbrella_body_base() {
    intersection() {
        umbrella_body_unclipped();
        translate([-40,-20,-50]) cube([80,21.0,100]);
    }
}

module umbrella_body() {
    difference() {
        umbrella_body_base();
        front_text();
        hamburg_mark();
    }
}

module text_2d() {
    offset(delta=0.12) text("Schietwetter",
        size=4.05,
        font="DejaVu Sans:style=Bold Oblique",
        halign="center",
        valign="center",
        spacing=0.86);
}

module front_text() {
    translate([0,-0.70,4.90])
        rotate([90,0,0])
            linear_extrude(height=3.50, convexity=10)
                text_2d();
}

module tower_shape_2d(cx, base_y, w, h) {
    union() {
        translate([cx-w/2,base_y]) square([w,h*0.70]);
        polygon(points=[
            [cx-w/2, base_y+h*0.70],
            [cx+w/2, base_y+h*0.70],
            [cx,     base_y+h]
        ]);
    }
}

module hamburg_mark_2d() {
    union() {
        translate([-6.3,-2.1]) square([12.6,1.15]);
        tower_shape_2d(-4.3,-1.0,2.25,3.4);
        tower_shape_2d( 0.0,-1.0,2.55,4.4);
        tower_shape_2d( 4.3,-1.0,2.25,3.4);
    }
}

module hamburg_mark() {
    translate([0,-0.70,9.30])
        rotate([90,0,0])
            linear_extrude(height=3.00, convexity=10)
                scale([1.0,0.85]) hamburg_mark_2d();
}

if (part == "body") {
    umbrella_body();
} else if (part == "text") {
    front_text();
} else if (part == "mark") {
    hamburg_mark();
} else {
    color(body_blue) umbrella_body();
    color(text_cream) front_text();
    color(mark_red) hamburg_mark();
}
