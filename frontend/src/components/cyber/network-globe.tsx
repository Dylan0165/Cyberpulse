"use client";

import { useRef, useState, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";

export interface GlobeTarget {
  id: string;
  label: string;
  risk: number; // 0-100
}

function latLngToVec3(lat: number, lng: number, radius: number): THREE.Vector3 {
  const phi = (90 - lat) * (Math.PI / 180);
  const theta = (lng + 180) * (Math.PI / 180);
  return new THREE.Vector3(
    -radius * Math.sin(phi) * Math.cos(theta),
    radius * Math.cos(phi),
    radius * Math.sin(phi) * Math.sin(theta)
  );
}

// Deterministic pseudo-coords from an id string
function idToLatLng(id: string): [number, number] {
  let h = 0;
  for (let i = 0; i < id.length; i++) h = (h * 31 + id.charCodeAt(i)) & 0xffffff;
  const lat = (h % 180) - 90;
  const lng = ((h >> 8) % 360) - 180;
  return [lat, lng];
}

function GlobeScene({ targets }: { targets: GlobeTarget[] }) {
  const group = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState<string | null>(null);
  const radius = 2;

  useFrame((_, delta) => {
    if (group.current && !hovered) {
      group.current.rotation.y += delta * 0.12;
    }
  });

  const points = useMemo(
    () =>
      targets.map((t) => {
        const [lat, lng] = idToLatLng(t.id);
        return { ...t, pos: latLngToVec3(lat, lng, radius + 0.02) };
      }),
    [targets]
  );

  return (
    <group ref={group}>
      {/* Wireframe sphere */}
      <mesh>
        <sphereGeometry args={[radius, 32, 32]} />
        <meshBasicMaterial color="#0A2035" wireframe transparent opacity={0.5} />
      </mesh>
      <mesh>
        <sphereGeometry args={[radius * 0.99, 32, 32]} />
        <meshBasicMaterial color="#050D14" transparent opacity={0.85} />
      </mesh>

      {/* Target points */}
      {points.map((p) => {
        const high = p.risk >= 60;
        const color = high ? "#FF2D55" : p.risk >= 30 ? "#FFD60A" : "#00FF88";
        return (
          <mesh
            key={p.id}
            position={p.pos}
            onPointerOver={() => setHovered(p.id)}
            onPointerOut={() => setHovered(null)}
          >
            <sphereGeometry args={[high ? 0.07 : 0.045, 12, 12]} />
            <meshBasicMaterial color={color} />
            {hovered === p.id && (
              <Html distanceFactor={8} zIndexRange={[100, 0]}>
                <div className="whitespace-nowrap rounded-md border border-grid bg-card2 px-2 py-1 font-mono text-[10px] text-ink shadow-glow-cyan">
                  {p.label} · risk {p.risk}
                </div>
              </Html>
            )}
          </mesh>
        );
      })}
    </group>
  );
}

export default function NetworkGlobe({ targets }: { targets: GlobeTarget[] }) {
  return (
    <Canvas camera={{ position: [0, 0, 6], fov: 45 }} dpr={[1, 1.5]} frameloop="always">
      <ambientLight intensity={0.6} />
      <pointLight position={[5, 5, 5]} intensity={0.8} color="#00D4FF" />
      <GlobeScene targets={targets} />
      <OrbitControls enableZoom={false} enablePan={false} rotateSpeed={0.5} />
    </Canvas>
  );
}
