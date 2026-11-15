import sys
import numpy as np
import trimesh

path = sys.argv[1] if len(sys.argv) > 1 else "../samples/bracket.stl"
mesh = trimesh.load(path, force="mesh") # one mesh

print("watertight:", mesh.is_watertight) # fully closed for reliable volume measurement
print("volume (mm^3):", round(mesh.volume, 1)) # space inside part
print("surface area (mm^2):", round(mesh.area, 1)) # total outside surface
print("bounding box (mm):", mesh.extents.round(1)) # size of smallest box around the part [x,y,z]

# Wall thickness
pts, face_idx = trimesh.sample.sample_surface(mesh, 3000) #3000 random spots to return pts
normals = mesh.face_normals[face_idx] # one arrow sticking out of each of the 3000 points
origins = pts - normals * 1e-4
locs, ray_idx, _ = mesh.ray.intersects_location(
    origins, -normals, multiple_hits=False
)
thickness = np.linalg.norm(locs - origins[ray_idx], axis=1) #finding distance travelled

print("thickness min (mm):", round(thickness.min(), 2))
print("thickness median (mm):", round(float(np.median(thickness)), 2))
print("points thinner than 1.5 mm:", int((thickness < 1.5).sum()), "of", len(thickness))