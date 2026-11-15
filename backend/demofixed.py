import trimesh


def box(size, center):
    m = trimesh.creation.box(extents=size)
    m.apply_translation(center)
    return m


def wedge(p0, p1, p2, y0=-20, y1=20):
    """Triangular prism: a triangle in the X-Z plane, extruded along Y.

    The triangle's points must run clockwise in X-Z, as they do below.
    """
    verts = [[p[0], y, p[1]] for y in (y0, y1) for p in (p0, p1, p2)]
    faces = [
        [0, 2, 1], [3, 4, 5],                    # the two triangular ends
        [0, 1, 4], [0, 4, 3],                    # the three rectangular sides
        [1, 2, 5], [1, 5, 4],
        [2, 0, 3], [2, 3, 5],
    ]
    m = trimesh.Trimesh(vertices=verts, faces=faces)
    if m.volume < 0:                             # safety: make normals point out
        m.invert()
    return m


# Dimensions in mm. Parts overlap slightly so they fuse into one solid.
base = box((60, 40, 6), (0, 0, 3))              # base plate, z 0..6
wall = box((3.0, 40, 30), (-20, 0, 20))         # FIX 1: 3 mm wall (was 1 mm)
block = box((10, 40, 25), (20, 0, 17.5))        # support block
shelf = box((24, 40, 3), (27, 0, 29.5))         # shorter shelf, x 15..39
gusset = wedge((24, 8), (24, 28.5), (39.4, 28.5))  # FIX 2: steep support under shelf

part = trimesh.boolean.union([base, wall, block, shelf, gusset], engine="manifold")
part.export("../samples/demo_fixed.stl")

print("watertight:", part.is_watertight)
print("volume (mm^3):", round(part.volume, 1))
print("bounding box (mm):", part.extents.round(1))