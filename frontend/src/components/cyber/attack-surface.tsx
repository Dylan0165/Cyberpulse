"use client";

import { useRef, useState, useMemo } from "react";
import { Canvas, useFrame } from "@react-three/fiber";
import { OrbitControls, Html } from "@react-three/drei";
import * as THREE from "three";

export interface SurfaceNode {
  id: string;
  port: number;
  service: string;
  severity: string; // critical|high|medium|low|info
}

const SEV_COLOR: Record<string, string> = {
  critical: "#FF2D55",
  high: "#FF8C00",
  medium: "#FFD60A",
  low: "#0A84FF",
  info: "#4A6880",
};
const SEV_SIZE: Record<string, number> = {
  critical: 0.45, high: 0.36, medium: 0.28, low: 0.22, info: 0.18,
};

function Scene({ nodes, onSelect }: { nodes: SurfaceNode[]; onSelect: (n: SurfaceNode) => void }) {
  const group = useRef<THREE.Group>(null);
  const [hovered, setHovered] = useState<string | null>(null);

  useFrame((_, delta) => {
    if (group.current && !hovered) group.current.rotation.y += delta * 0.15;
  });

  const placed = useMemo(() => {
    const n = nodes.length || 1;
    return nodes.map((node, i) => {
      // distribute on a sphere (fibonacci)
      const phi = Math.acos(1 - (2 * (i + 0.5)) / n);
      const theta = Math.PI * (1 + Math.sqrt(5)) * i;
      const radius = 2.4;
      return {
        ...node,
        pos: new THREE.Vector3(
          radius * Math.sin(phi) * Math.cos(theta),
          radius * Math.cos(phi),
          radius * Math.sin(phi) * Math.sin(theta)
        ),
      };
    });
  }, [nodes]);

  return (
    <group ref={group}>
      {/* connection lines between same-service nodes */}
      {placed.map((a, i) =>
        placed.slice(i + 1).map((b) =>
          a.service === b.service ? (
            <line key={`${a.id}-${b.id}`}>
              <bufferGeometry
                attach="geometry"
                onUpdate={(g) => g.setFromPoints([a.pos, b.pos])}
              />
              <lineBasicMaterial attach="material" color="#0A2035" transparent opacity={0.6} />
            </line>
          ) : null
        )
      )}

      {placed.map((node) => {
        const sev = (node.severity || "info").toLowerCase();
        const color = SEV_COLOR[sev] ?? SEV_COLOR.info;
        const size = SEV_SIZE[sev] ?? 0.2;
        return (
          <mesh
            key={node.id}
            position={node.pos}
            onPointerOver={() => setHovered(node.id)}
            onPointerOut={() => setHovered(null)}
            onClick={() => onSelect(node)}
          >
            <icosahedronGeometry args={[size, 1]} />
            <meshStandardMaterial color={color} emissive={color} emissiveIntensity={0.5} />
            {hovered === node.id && (
              <Html distanceFactor={10} zIndexRange={[100, 0]}>
                <div className="whitespace-nowrap rounded-md border border-grid bg-card2 px-2 py-1 font-mono text-[10px] text-ink shadow-glow-cyan">
                  :{node.port} {node.service}
                </div>
              </Html>
            )}
          </mesh>
        );
      })}
    </group>
  );
}

export default function AttackSurface({
  nodes,
  onSelect,
}: {
  nodes: SurfaceNode[];
  onSelect?: (n: SurfaceNode) => void;
}) {
  return (
    <Canvas camera={{ position: [0, 0, 7], fov: 45 }} dpr={[1, 1.5]}>
      <ambientLight intensity={0.5} />
      <pointLight position={[6, 6, 6]} intensity={1} color="#00D4FF" />
      <pointLight position={[-6, -6, -6]} intensity={0.6} color="#FF2D55" />
      <Scene nodes={nodes} onSelect={onSelect ?? (() => {})} />
      <OrbitControls enableZoom enablePan={false} rotateSpeed={0.6} />
    </Canvas>
  );
}
