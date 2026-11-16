import { useEffect, useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, OrbitControls } from "@react-three/drei";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import * as THREE from "three";

const API = "http://127.0.0.1:8000";
const money = (x) => `$${x.toFixed(2)}`;
const card = {
  background: "#171c22",
  border: "1px solid #2a2f36",
  borderRadius: 8,
  padding: "10px 12px",
  margin: "12px 0",
};

function Part({ geometry }) {
  return (
    <mesh geometry={geometry}>
      <meshStandardMaterial color="#9aa7b5" metalness={0.2} roughness={0.6} />
    </mesh>
  );
}

function ThinPoints({ points }) {
  return points.map((p, i) => (
    <mesh key={i} position={p}>
      <sphereGeometry args={[0.8, 8, 8]} />
      <meshBasicMaterial color="red" />
    </mesh>
  ));
}

function Overhangs({ triangles }) {
  const geo = useMemo(() => {
    const g = new THREE.BufferGeometry();
    g.setAttribute(
      "position",
      new THREE.Float32BufferAttribute(triangles.flat(2), 3)
    );
    return g;
  }, [triangles]);
  return (
    <mesh geometry={geo}>
      <meshBasicMaterial
        color="orange"
        side={THREE.DoubleSide}
        polygonOffset
        polygonOffsetFactor={-2}
      />
    </mesh>
  );
}

function delta(before, after) {
  const diff = after - before;
  const pct = (diff / before) * 100;
  const sign = diff > 0 ? "+" : "−";
  return `${sign}$${Math.abs(diff).toFixed(2)} (${sign}${Math.abs(pct).toFixed(0)}%)`;
}

function Breakdown({ parts }) {
  return (
    <table style={{ width: "100%", fontSize: 13, opacity: 0.85, marginTop: 6 }}>
      <tbody>
        {Object.entries(parts).map(([name, value]) => (
          <tr key={name}>
            <td>{name.replace("_", " ")}</td>
            <td style={{ textAlign: "right" }}>{money(value)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

function Curve({ points }) {
  return (
    <table style={{ width: "100%", fontSize: 13, opacity: 0.85, marginTop: 6 }}>
      <thead>
        <tr>
          <th style={{ textAlign: "left" }}>Qty</th>
          <th style={{ textAlign: "right" }}>Each</th>
        </tr>
      </thead>
      <tbody>
        {points.map((p) => (
          <tr key={p.qty}>
            <td>{p.qty}</td>
            <td style={{ textAlign: "right" }}>{money(p.unit_price)}</td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}

export default function App() {
  const [file, setFile] = useState(null);
  const [geometry, setGeometry] = useState(null);
  const [result, setResult] = useState(null);
  const [prev, setPrev] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [materials, setMaterials] = useState({ print: ["PLA"], cnc: ["Aluminium 6061"] });
  const [printMat, setPrintMat] = useState("PLA");
  const [cncMat, setCncMat] = useState("Aluminium 6061");
  const [qty, setQty] = useState(1);

  // Ask the API which materials exist, once, when the page opens.
  useEffect(() => {
    fetch(`${API}/materials`)
      .then((r) => r.json())
      .then(setMaterials)
      .catch(() => {});
  }, []);

  async function analyse(f, pm, cm, q, isNewFile) {
    const before = result;
    setError("");
    setLoading(true);
    try {
      const form = new FormData();
      form.append("file", f);
      form.append("print_material", pm);
      form.append("cnc_material", cm);
      form.append("qty", String(q));
      const res = await fetch(`${API}/analyze`, { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json()).detail || "Analysis failed");
      const data = await res.json();
      if (isNewFile) setPrev(before);
      setResult(data);
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  }

  async function onFile(e) {
    const f = e.target.files[0];
    if (!f) return;
    setFile(f);
    setGeometry(new STLLoader().parse(await f.arrayBuffer()));
    analyse(f, printMat, cncMat, qty, true);
  }

  // Material or quantity changed: re-price the same file. The API has the
  // geometry cached, so this is fast.
  function onSettings(pm, cm, q) {
    setPrintMat(pm);
    setCncMat(cm);
    setQty(q);
    if (file) analyse(file, pm, cm, q, false);
  }

  const p = result?.print;
  const c = result?.cnc;

  return (
    <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", height: "100%" }}>
      <aside style={{ padding: 20, borderRight: "1px solid #2a2f36", overflow: "auto" }}>
        <h2 style={{ marginTop: 0 }}>CostCAD</h2>
        <input type="file" accept=".stl" onChange={onFile} />

        <div style={{ display: "grid", gap: 8, marginTop: 14, fontSize: 14 }}>
          <label>
            Print material{" "}
            <select value={printMat} onChange={(e) => onSettings(e.target.value, cncMat, qty)}>
              {materials.print.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>
          <label>
            CNC material{" "}
            <select value={cncMat} onChange={(e) => onSettings(printMat, e.target.value, qty)}>
              {materials.cnc.map((m) => (
                <option key={m}>{m}</option>
              ))}
            </select>
          </label>
          <label>
            Quantity{" "}
            <input
              type="number"
              min="1"
              value={qty}
              style={{ width: 70 }}
              onChange={(e) =>
                onSettings(printMat, cncMat, Math.max(1, parseInt(e.target.value, 10) || 1))
              }
            />
          </label>
        </div>

        {loading && <p>Analysing…</p>}
        {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}

        {result && (
          <>
            {prev && (
              <div style={card}>
                <b>Vs previous part</b>
                <div>Print: {delta(prev.print.unit_price, p.unit_price)}</div>
                {prev.cnc.suitable && c.suitable && (
                  <div>CNC: {delta(prev.cnc.unit_price, c.unit_price)}</div>
                )}
              </div>
            )}

            <div style={card}>
              <b>3D print · {p.material}</b>
              <div style={{ fontSize: 26, margin: "4px 0" }}>
                {money(p.unit_price)} <span style={{ fontSize: 13, opacity: 0.6 }}>each</span>
              </div>
              <div style={{ fontSize: 13 }}>
                Print it <b>{p.orientation}</b>
                {p.as_saved_price > p.unit_price && (
                  <> to save {money(p.as_saved_price - p.unit_price)} vs. as saved</>
                )}
              </div>
              <Breakdown parts={p.breakdown} />
              <Curve points={p.curve} />
            </div>

            <div style={card}>
              <b>CNC · {c.material}</b>
              {c.suitable ? (
                <>
                  <div style={{ fontSize: 26, margin: "4px 0" }}>
                    {money(c.unit_price)} <span style={{ fontSize: 13, opacity: 0.6 }}>each</span>
                  </div>
                  <div style={{ fontSize: 13 }}>
                    {c.setups.length} setups ({c.setups.join(", ")}) · {c.waste_pct}% of the
                    block becomes chips
                  </div>
                  <Breakdown parts={c.breakdown} />
                  <Curve points={c.curve} />
                </>
              ) : (
                <p style={{ color: "#ffb347", fontSize: 14 }}>
                  Not suitable for 3-axis CNC: {c.unreachable_pct}% of the surface can't be
                  reached by a cutter. Print it, or use a 5-axis shop.
                </p>
              )}
            </div>

            <h3>Issues</h3>
            <p style={{ color: "red" }}>Thin-wall points: {result.issues.thin_wall_count}</p>
            <p style={{ color: "orange" }}>
              Needs support: {result.issues.overhang_area_mm2} mm² (in the recommended orientation)
            </p>
            <p style={{ opacity: 0.7, fontSize: 13 }}>
              Fixing the issues would save {money(result.savings_if_fixed.print)} (print) /{" "}
              {money(result.savings_if_fixed.cnc)} (CNC)
            </p>
            <p style={{ opacity: 0.6, fontSize: 13 }}>
              Size: {result.bounding_box_mm.join(" × ")} mm · {result.volume_cm3} cm³ solid,{" "}
              {p.plastic_cm3} cm³ printed
              <br />
              Watertight: {String(result.watertight)}
            </p>
          </>
        )}
      </aside>

      <Canvas camera={{ position: [120, 90, 120], far: 5000 }}>
        <ambientLight intensity={0.7} />
        <directionalLight position={[100, 200, 100]} intensity={1.2} />
        <OrbitControls makeDefault />
        <Bounds fit clip observe margin={1.3}>
          {/* STL files are Z-up, three.js is Y-up, so rotate the group */}
          <group rotation={[-Math.PI / 2, 0, 0]}>
            {geometry && <Part geometry={geometry} />}
            {result && <ThinPoints points={result.issues.thin_wall_points} />}
            {result && <Overhangs triangles={result.issues.overhang_triangles} />}
          </group>
        </Bounds>
      </Canvas>
    </div>
  );
}