import trimesh


def box(size, center):
    m = trimesh.creation.box(extents=size)
    m.apply_translation(center)
    return m


# Dimensions in mm. Parts overlap slightly so they become one solid.
base = box((60, 40, 6), (0, 0, 3))          # base plate, z 0..6
thin_wall = box((1.0, 40, 30), (-20, 0, 20))  #1 mm wall
block = box((10, 40, 25), (20, 0, 17.5))     # support block
shelf = box((30, 40, 3), (30, 0, 29.5))      #shelf hanging over air

part = trimesh.boolean.union([base, thin_wall, block, shelf], engine="manifold")
part.export("../samples/demo_flawed.stl")

print("watertight:", part.is_watertight)
print("volume (mm^3):", round(part.volume, 1))
print("bounding box (mm):", part.extents.round(1))