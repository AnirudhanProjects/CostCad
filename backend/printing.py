"""3D-print pricing: shell + infill, support volume, best orientation."""
import numpy as np
from trimesh.transformations import rotation_matrix

import materials as M
from checks import overhang_faces

SHELL_MM = 1.2          # solid outer walls: 3 lines from a 0.4 mm nozzle
INFILL = 0.15           # 15% sparse fill inside the walls
SUPPORT_DENSITY = 0.15  # support is printed as a sparse lattice too

# The six ways a part can sit on the bed, named by which side faces down.
ORIENTATIONS = {
    "bottom down (as saved)": np.eye(4),
    "top down": rotation_matrix(np.pi, [1, 0, 0]),
    "front down": rotation_matrix(np.pi / 2, [1, 0, 0]),    # -Y side down
    "back down": rotation_matrix(-np.pi / 2, [1, 0, 0]),    # +Y side down
    "right down": rotation_matrix(np.pi / 2, [0, 1, 0]),    # +X side down
    "left down": rotation_matrix(-np.pi / 2, [0, 1, 0]),    # -X side down
}


def place_on_bed(mesh, matrix):
    """Rotate a copy of the part, then drop it so its lowest point is z = 0."""
    m = mesh.copy()
    m.apply_transform(matrix)
    m.apply_translation([0, 0, -m.bounds[0][2]])
    return m


def deposited_volume_cm3(mesh):
    """Plastic actually printed: a solid shell plus sparse infill inside."""
    vol = mesh.volume
    shell = min(vol, mesh.area * SHELL_MM)   # thin parts are all shell
    return (shell + INFILL * (vol - shell)) / 1000


def support_volume_cm3(mesh, faces):
    """Support needed under the overhanging faces.

    For each overhanging triangle, shoot a ray straight down. The support
    column runs from the triangle to whatever the ray hits first: another
    part of the model, or the bed.
    """
    if len(faces) == 0:
        return 0.0
    centers = mesh.triangles_center[faces]
    normals = mesh.face_normals[faces]
    footprint = mesh.area_faces[faces] * np.abs(normals[:, 2])  # area seen from below
    origins = centers + normals * 1e-3                          # step just outside
    down = np.tile([0.0, 0.0, -1.0], (len(faces), 1))
    hits, ray_idx, _ = mesh.ray.intersects_location(origins, down, multiple_hits=False)
    height = centers[:, 2] - mesh.bounds[0][2]                  # default: to the bed
    if len(ray_idx):                                            # or to the part below
        height[ray_idx] = centers[ray_idx, 2] - hits[:, 2]
    return float((footprint * height).sum()) * SUPPORT_DENSITY / 1000


def analyse_print(mesh):
    """The slow geometry work. Run once per file, then price it many times."""
    options = []
    for name, matrix in ORIENTATIONS.items():
        m = place_on_bed(mesh, matrix)
        faces = overhang_faces(m)
        options.append({
            "name": name,
            "faces": faces,
            "overhang_area_mm2": float(m.area_faces[faces].sum()),
            "support_cm3": support_volume_cm3(m, faces),
        })
    return {"part_cm3": deposited_volume_cm3(mesh), "options": options}


def price_print(geom, material, qty=1):
    """Price every orientation. Returns (best, as_saved, all_options)."""
    mat = M.PRINT_MATERIALS[material]
    # Each cm3 of plastic costs its material plus the printer time to lay it down.
    per_cm3 = mat["density"] * mat["price_per_g"] + M.PRINT_MACHINE_PER_H / M.PRINT_RATE_CM3_PER_H
    priced = []
    for opt in geom["options"]:
        parts = {
            "plastic": geom["part_cm3"] * per_cm3,
            "support": opt["support_cm3"] * per_cm3
            + opt["overhang_area_mm2"] / 100 * M.CLEANUP_PER_CM2,
            "setup": M.PRINT_SETUP / qty,
        }
        parts = {k: v * M.PRINT_PRICE_FACTOR for k, v in parts.items()}
        priced.append({**opt, "breakdown": parts, "unit_price": sum(parts.values())})
    best = min(priced, key=lambda p: p["unit_price"])
    return best, priced[0], priced