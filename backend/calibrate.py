"""Compare CostCAD's prices with real quotes, and suggest correction factors.

Usage (from the backend folder):
    python calibrate.py ../calibration/quotes.csv

Each row of the CSV is one real quote you collected:
    file,process,material,qty,quoted_unit_price,source,date
'file' is relative to the CSV's folder, 'process' is print or cnc, and
'material' must match a name in materials.py.
"""
import csv
import sys
from pathlib import Path

import numpy as np
import trimesh

import materials as M
from machining import analyse_cnc, price_cnc
from printing import analyse_print, price_print

csv_path = Path(sys.argv[1])
with open(csv_path, newline="") as f:
    rows = list(csv.DictReader(f))
if not rows:
    sys.exit("No quotes yet. Add rows to the CSV first.")

results = {"print": [], "cnc": []}
for row in rows:
    mesh = trimesh.load(csv_path.parent / row["file"], force="mesh")
    qty = int(row["qty"])
    quote = float(row["quoted_unit_price"])
    if row["process"] == "print":
        model = price_print(analyse_print(mesh), row["material"], qty)[0]["unit_price"]
    else:
        model = price_cnc(analyse_cnc(mesh), row["material"], qty)["unit_price"]
    results[row["process"]].append((quote, model))
    error = (model - quote) / quote * 100
    print(f'{row["file"]:32} {row["process"]:5} qty {qty:<4} '
          f'quote ${quote:8.2f}   model ${model:8.2f}   {error:+6.1f}%')

for process, pairs in results.items():
    if not pairs:
        continue
    quotes = np.array([q for q, _ in pairs])
    models = np.array([m for _, m in pairs])
    error_now = np.mean(np.abs(models - quotes) / quotes) * 100
    factor = float(np.median(quotes / models))
    error_after = np.mean(np.abs(models * factor - quotes) / quotes) * 100
    current = M.PRINT_PRICE_FACTOR if process == "print" else M.CNC_PRICE_FACTOR
    print(f"\n{process}: {len(pairs)} quotes, average error {error_now:.0f}%")
    print(f"  multiplying by {factor:.2f} would bring it to {error_after:.0f}%")
    print(f"  -> set {process.upper()}_PRICE_FACTOR = {current * factor:.2f} in materials.py")