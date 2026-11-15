import io

import trimesh
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from checks import overhang_faces, thin_wall_points
from cost import cnc_cost, print_cost

app = FastAPI(title="CostCAD")

# Lets the React dev server (added later) talk to this API.
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

    thin_pts, thin_vals = thin_wall_points(mesh)
    bad = overhang_faces(mesh)

    return {
        "volume_mm3": round(float(mesh.volume), 1),
        "bounding_box_mm": mesh.extents.round(1).tolist(),
        "watertight": bool(mesh.is_watertight),
        "cost": {
            "print_pla": round(float(print_cost(mesh)), 2),
            "cnc_aluminium": round(float(cnc_cost(mesh)), 2),
        },
        "issues": {
            "thin_wall_points": thin_pts[:500].round(2).tolist(),
            "overhang_triangles": mesh.triangles[bad][:500].round(2).tolist(),
            "overhang_area_mm2": round(float(mesh.area_faces[bad].sum()), 1),
        },
    }