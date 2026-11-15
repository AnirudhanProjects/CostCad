import { useMemo, useState } from "react";
import { Canvas } from "@react-three/fiber";
import { Bounds, OrbitControls } from "@react-three/drei";
import { STLLoader } from "three/examples/jsm/loaders/STLLoader.js";
import * as THREE from "three";

const API = "http://127.0.0.1:8000";

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

export default function App() {
  const [geometry, setGeometry] = useState(null);
  const [result, setResult] = useState(null);
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [prev, setPrev] = useState(null);

  async function onFile(e) {
    const file = e.target.files[0];
    if (!file) return;
    const before = result;
    setError("");
    setResult(null);
    setLoading(true);
    try {
      const buf = await file.arrayBuffer();
      setGeometry(new STLLoader().parse(buf));

      const form = new FormData();
      form.append("file", file);
      const res = await fetch(`${API}/analyze`, { method: "POST", body: form });
      if (!res.ok) throw new Error((await res.json()).detail || "Analysis failed");
      const data = await res.json();
      setPrev(before);
      setResult(data);
    } catch (err) {
      setError(String(err.message || err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", height: "100%" }}>
      <aside style={{ padding: 20, borderRight: "1px solid #2a2f36", overflow: "auto" }}>
        <h2 style={{ marginTop: 0 }}>CostCAD</h2>
        <input type="file" accept=".stl" onChange={onFile} />
        {loading && <p>Analysing…</p>}
        {error && <p style={{ color: "#ff6b6b" }}>{error}</p>}
        {result && (
          <div>
            <h3>Cost</h3>
            <p>3D print (PLA): <b>${result.cost.print_pla}</b></p>
            <p>CNC (aluminium): <b>${result.cost.cnc_aluminium}</b></p>
            <p style={{ opacity: 0.7, fontSize: 13 }}>
              Fixing the issues would save ${result.savings_if_fixed.print_pla} (print)
              / ${result.savings_if_fixed.cnc_aluminium} (CNC)
            </p>
            {prev && (
              <div
                style={{
                  background: "#1d2530",
                  border: "1px solid #3a4655",
                  borderRadius: 8,
                  padding: "8px 12px",
                  margin: "12px 0",
                }}
              >
                <b>Vs previous upload</b>
                <div>Print: {delta(prev.cost.print_pla, result.cost.print_pla)}</div>
                <div>
                  CNC: {delta(prev.cost.cnc_aluminium, result.cost.cnc_aluminium)}
                </div>
              </div>
            )}
            <h3>Issues</h3>
            <p style={{ color: "red" }}>
              Thin-wall points: {result.issues.thin_wall_count}
            </p>
            <p style={{ color: "orange" }}>
              Overhang area: {result.issues.overhang_area_mm2} mm²
            </p>
            <p style={{ opacity: 0.6, fontSize: 13 }}>
              Size: {result.bounding_box_mm.join(" × ")} mm
              <br />
              Watertight: {String(result.watertight)}
            </p>
          </div>
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