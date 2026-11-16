"""CNC pricing, plus a check for whether a 3-axis mill can make the part."""
import numpy as np
import trimesh

import materials as M

# A 3-axis mill cuts from above. Flipping the part between setups lets it
# reach other sides. These are the six directions a cutter can come from.
APPROACHES = {
    "top": [0, 0, 1],
    "bottom": [0, 0, -1],
    "front": [0, -1, 0],
    "back": [0, 1, 0],
    "left": [-1, 0, 0],
    "right": [1, 0, 0],
}
MIN_SHARE_FOR_SETUP = 0.005   # a side counts as a setup if it reaches 0.5% of the surface
MAX_UNREACHABLE = 0.02        # more than 2% unreachable -> not a 3-axis part


def analyse_cnc(mesh, n=2000):
    """Which setups are needed, and how much surface no setup can reach."""
    pts, face_idx = trimesh.sample.sample_surface(mesh, n, seed=1)
    normals = mesh.face_normals[face_idx]
    reached = np.zeros(n, dtype=bool)
    setups = []
    for name, d in APPROACHES.items():
        d = np.array(d, dtype=float)
        # Surfaces facing this direction are cut by the tip of the tool, and
        # walls parallel to it by the side of the tool. Surfaces facing away can't be cut.
        candidates = np.where(~reached & (normals @ d > -0.05))[0]
        if len(candidates) == 0:
            continue
        # A point is reachable if a straight line out along d escapes the part.
        origins = pts[candidates] + normals[candidates] * 0.05
        dirs = np.tile(d, (len(candidates), 1))
        blocked = mesh.ray.intersects_any(origins, dirs)
        newly = candidates[~blocked]
        reached[newly] = True
        if len(newly) / n >= MIN_SHARE_FOR_SETUP:
            setups.append(name)

    ex = mesh.extents + 10                      # block with 5 mm spare per side
    stock = float(ex[0] * ex[1] * ex[2]) / 1000
    removed = stock - float(mesh.volume) / 1000
    return {
        "setups": setups,
        "unreachable_share": float(1 - reached.mean()),
        "stock_cm3": stock,
        "removed_cm3": removed,
    }


def price_cnc(geom, material, qty=1, thin_area_mm2=0.0):
    mat = M.CNC_MATERIALS[material]
    setup = M.CNC_SETUP + M.CNC_EXTRA_SETUP * max(0, len(geom["setups"]) - 1)
    parts = {
        "stock": geom["stock_cm3"] * mat["density"] * mat["price_per_g"],
        "machining": geom["removed_cm3"] / mat["removal_cm3_per_h"] * M.CNC_MACHINE_PER_H,
        "thin_walls": thin_area_mm2 * M.THIN_WALL_COST_PER_MM2,
        "setup": setup / qty,
    }
    parts = {k: v * M.CNC_PRICE_FACTOR for k, v in parts.items()}
    return {
        "breakdown": parts,
        "unit_price": sum(parts.values()),
        "suitable": geom["unreachable_share"] <= MAX_UNREACHABLE,
    }