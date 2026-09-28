from __future__ import annotations

import cadquery as cq


def build_model():
    return (
        cq.Workplane("XY")
        .box(30.0, 20.0, 8.0)
        .edges("|Z")
        .fillet(2.0)
        .faces(">Z")
        .workplane()
        .hole(5.0)
    )
