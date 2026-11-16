import hashlib
import io

import trimesh
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

import materials as M
from checks import thin_wall_points
from machining import analyse_cnc, price_cnc
from printing import analyse_print, price_print

app = FastAPI(title="CostCAD")
N_SAMPLES = 3000
QTY_CURVE = [1, 10, 50, 100]

# Lets the React dev server talk to this API.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# The geometry work is slow, pricing is fast. Remember the geometry for each
# file (by a fingerprint of its bytes), so changing material or quantity is instant.
_cache = {}


def r2(x):
    return round(float(x), 2)


def analyse_geometry(data):
    key = hashlib.sha1(data).hexdigest()
    if key not in _cache:
        try:
            mesh = trimesh.load(io.BytesIO(data), file_type="stl", force="mesh")
        except Exception:
            raise ValueError("Could not read that file as an STL.")
        if len(mesh.faces) == 0:
            raise ValueError("That STL has no triangles in it.")

        thin_pts, _ = thin_wall_points(mesh, n=N_SAMPLES)
        thin_area = len(thin_pts) / N_SAMPLES * mesh.area if len(thin_pts) >= 10 else 0.0

        if len(_cache) >= 20:
            _cache.clear()
        _cache[key] = {
            "mesh": mesh,
            "thin_pts": thin_pts,
            "thin_area": float(thin_area),
            "print": analyse_print(mesh),
            "cnc": analyse_cnc(mesh),
        }
    return _cache[key]


def build_report(data, print_material, cnc_material, qty):
    g = analyse_geometry(data)
    mesh = g["mesh"]

    best, as_saved, options = price_print(g["print"], print_material, qty)
    cnc = price_cnc(g["cnc"], cnc_material, qty, g["thin_area"])

    return {
        "volume_cm3": r2(mesh.volume / 1000),
        "bounding_box_mm": mesh.extents.round(1).tolist(),
        "watertight": bool(mesh.is_watertight),
        "qty": qty,
        "print": {
            "material": print_material,
            "unit_price": r2(best["unit_price"]),
            "breakdown": {k: r2(v) for k, v in best["breakdown"].items()},
            "orientation": best["name"],
            "as_saved_price": r2(as_saved["unit_price"]),
            "orientations": [
                {"name": o["name"], "unit_price": r2(o["unit_price"])} for o in options
            ],
            "plastic_cm3": r2(g["print"]["part_cm3"]),
            "support_cm3": r2(best["support_cm3"]),
            "curve": [
                {"qty": q, "unit_price": r2(price_print(g["print"], print_material, q)[0]["unit_price"])}
                for q in QTY_CURVE
            ],
        },
        "cnc": {
            "material": cnc_material,
            "suitable": cnc["suitable"],
            "unit_price": r2(cnc["unit_price"]),
            "breakdown": {k: r2(v) for k, v in cnc["breakdown"].items()},
            "setups": g["cnc"]["setups"],
            "unreachable_pct": r2(g["cnc"]["unreachable_share"] * 100),
            "waste_pct": r2(g["cnc"]["removed_cm3"] / g["cnc"]["stock_cm3"] * 100),
            "curve": [
                {"qty": q, "unit_price": r2(price_cnc(g["cnc"], cnc_material, q, g["thin_area"])["unit_price"])}
                for q in QTY_CURVE
            ],
        },
        "savings_if_fixed": {
            "print": r2(best["breakdown"]["support"]),
            "cnc": r2(cnc["breakdown"]["thin_walls"]),
        },
        "issues": {
            "thin_wall_count": int(len(g["thin_pts"])) if len(g["thin_pts"]) >= 10 else 0,
            "thin_wall_area_mm2": r2(g["thin_area"]),
            "thin_wall_points": g["thin_pts"][:500].round(2).tolist(),
            # Overhangs in the recommended orientation, drawn on the part as saved.
            "overhang_triangles": mesh.triangles[best["faces"]][:500].round(2).tolist(),
            "overhang_area_mm2": r2(best["overhang_area_mm2"]),
        },
    }


@app.get("/materials")
def materials():
    return {"print": list(M.PRINT_MATERIALS), "cnc": list(M.CNC_MATERIALS)}


@app.post("/analyze")
async def analyze(
    file: UploadFile = File(...),
    print_material: str = Form("PLA"),
    cnc_material: str = Form("Aluminium 6061"),
    qty: int = Form(1),
):
    if print_material not in M.PRINT_MATERIALS or cnc_material not in M.CNC_MATERIALS:
        raise HTTPException(status_code=400, detail="Unknown material.")
    if qty < 1:
        raise HTTPException(status_code=400, detail="Quantity must be at least 1.")
    data = await file.read()
    try:
        return build_report(data, print_material, cnc_material, qty)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))