import io

import trimesh
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from checks import overhang_faces, thin_wall_points
from cost import cnc_cost, print_cost

app = FastAPI(title="CostCAD")
N_SAMPLES = 3000

# Lets the React dev server talk to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    data = await file.read()
    try:
        mesh = trimesh.load(io.BytesIO(data), file_type="stl", force="mesh")
    except Exception:
        raise HTTPException(status_code=400, detail="Could not read that file as an STL.")

    thin_pts, thin_vals = thin_wall_points(mesh, n=N_SAMPLES)
    bad = overhang_faces(mesh)

    overhang_area = float(mesh.area_faces[bad].sum())
    # Estimate thin area: the share of sample points that were thin,
    # times the total surface area. Ignore a handful of noisy points.
    thin_area = float(len(thin_pts) / N_SAMPLES * mesh.area)
    if len(thin_pts) < 10:
        thin_area = 0.0

    print_clean = float(print_cost(mesh))
    print_total = float(print_cost(mesh, overhang_area=overhang_area))
    cnc_clean = float(cnc_cost(mesh))
    cnc_total = float(cnc_cost(mesh, thin_area=thin_area))

    return {
        "volume_mm3": round(float(mesh.volume), 1),
        "bounding_box_mm": mesh.extents.round(1).tolist(),
        "watertight": bool(mesh.is_watertight),
        "cost": {
            "print_pla": round(print_total, 2),
            "cnc_aluminium": round(cnc_total, 2),
        },
        "savings_if_fixed": {
            "print_pla": round(print_total - print_clean, 2),
            "cnc_aluminium": round(cnc_total - cnc_clean, 2),
        },
        "issues": {
            "thin_wall_count": int(len(thin_pts)),
            "thin_wall_area_mm2": round(thin_area, 1),
            "thin_wall_points": thin_pts[:500].round(2).tolist(),
            "overhang_triangles": mesh.triangles[bad][:500].round(2).tolist(),
            "overhang_area_mm2": round(overhang_area, 1),
        },
    }