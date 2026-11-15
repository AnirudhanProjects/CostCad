import sys
import numpy as np
import trimesh


def thin_wall_points(mesh, limit_mm=1.5, n=3000):
    """Return the locations where the wall is thinner than limit_mm."""
    pts, face_idx = trimesh.sample.sample_surface(mesh, n)
    normals = mesh.face_normals[face_idx]
    origins = pts - normals * 1e-4
    locs, ray_idx, _ = mesh.ray.intersects_location(
        origins, -normals, multiple_hits=False
    )
    thickness = np.linalg.norm(locs - origins[ray_idx], axis=1)
    thin = thickness < limit_mm
    return origins[ray_idx][thin], thickness[thin]


def overhang_faces(mesh, max_angle_deg=45):
    """Return indices of triangles that overhang more than max_angle_deg.

    Assumes the part prints in the orientation it has in the file (Z is up).
    """
    limit = -np.sin(np.radians(max_angle_deg))
    facing_down = mesh.face_normals[:, 2] < limit
    on_bed = mesh.triangles_center[:, 2] < mesh.bounds[0][2] + 0.1
    return np.where(facing_down & ~on_bed)[0]


if __name__ == "__main__":
    mesh = trimesh.load(sys.argv[1], force="mesh")

    thin_pts, thin_vals = thin_wall_points(mesh)
    print("thin-wall points:", len(thin_pts))
    if len(thin_vals):
        print("  thinnest (mm):", round(float(thin_vals.min()), 2))

    bad = overhang_faces(mesh)
    overhang_area = mesh.area_faces[bad].sum()
    print("overhang triangles:", len(bad))
    print("overhang area (mm^2):", round(float(overhang_area), 1))
    print("overhang share of surface:", f"{overhang_area / mesh.area:.1%}")