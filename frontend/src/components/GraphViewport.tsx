import { useRef, useEffect, useCallback, useState } from 'react';
import * as THREE from 'three';
import type { MemoryNode, MemoryEdge, VisEvent } from '../types';
import './GraphViewport.css';

interface GraphViewportProps {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
  events: VisEvent[];
  onNodeClick: (node: MemoryNode) => void;
}

// Generates a stable 3D position based on node ID hash
function hashPosition3D(id: string): [number, number, number] {
  let h1 = 0;
  let h2 = 0;
  let h3 = 0;
  for (let i = 0; i < id.length; i++) {
    h1 = ((h1 << 5) - h1 + id.charCodeAt(i)) | 0;
    h2 = ((h2 << 7) - h2 + id.charCodeAt(i)) | 0;
    h3 = ((h3 << 3) - h3 + id.charCodeAt(i)) | 0;
  }
  const x = (Math.abs(h1 % 600) / 100) - 3;
  const y = (Math.abs(h2 % 400) / 100) - 2;
  const z = (Math.abs(h3 % 400) / 100) - 2;
  return [x, y, z];
}

interface NodeState {
  id: string;
  mesh: THREE.Mesh;
  targetPos: THREE.Vector3;
  targetScale: number;
  targetColor: THREE.Color;
  targetOpacity: number;
  data: MemoryNode;
  isConcept: boolean;
  position: THREE.Vector3;
  velocity: THREE.Vector3;
  force: THREE.Vector3;
}

export function GraphViewport({ nodes, edges, events, onNodeClick }: GraphViewportProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const mountRef = useRef<HTMLDivElement>(null);

  const [hoveredNode, setHoveredNode] = useState<MemoryNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });

  // Refs to hold lists of current node states and active edges
  const nodesMapRef = useRef<Map<string, NodeState>>(new Map());
  const edgesListRef = useRef<{ source: string; target: string; line: THREE.Line }[]>([]);

  // Event trackers
  const activatedRef = useRef<Set<string>>(new Set());
  const fadedRef = useRef<Set<string>>(new Set());
  const conceptsRef = useRef<Set<string>>(new Set());
  const clusterCentersRef = useRef<Map<number, [number, number, number]>>(new Map());
  const nodeToClusterCenterRef = useRef<Map<string, [number, number, number]>>(new Map());

  // Mouse interaction state
  const isDraggingRef = useRef<boolean>(false);
  const rotationRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const targetRotationRef = useRef<{ x: number; y: number }>({ x: 0, y: 0 });
  const zoomRef = useRef<number>(6.5);

  // Process VisEvents for animations
  useEffect(() => {
    for (const evt of events) {
      switch (evt.type) {
        case 'node_activate':
          evt.node_ids?.forEach(id => activatedRef.current.add(id));
          break;
        case 'node_merge':
        case 'node_fade':
          evt.node_ids?.forEach(id => fadedRef.current.add(id));
          break;
        case 'concept_create':
          if (evt.concept_label) conceptsRef.current.add(evt.concept_label);
          break;
        case 'cluster_form':
          if (evt.cluster_id !== undefined && evt.cluster_members) {
            const members = evt.cluster_members;
            let cx = 0, cy = 0, cz = 0, count = 0;
            for (const mid of members) {
              const pos = hashPosition3D(mid);
              cx += pos[0];
              cy += pos[1];
              cz += pos[2];
              count++;
            }
            if (count > 0) {
              const center = [cx / count, cy / count, cz / count] as [number, number, number];
              clusterCentersRef.current.set(evt.cluster_id, center);
              members.forEach(mid => {
                nodeToClusterCenterRef.current.set(mid, center);
              });
            }
          }
          break;
      }
    }
  }, [events]);

  // Main Three.js Init & Update logic
  useEffect(() => {
    const mountPoint = mountRef.current;
    if (!mountPoint) return;

    // Get exact dimensions of mount element
    const width = mountPoint.clientWidth || 600;
    const height = mountPoint.clientHeight || 400;

    // 1. Scene setup
    const scene = new THREE.Scene();

    // 2. Camera setup
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.z = zoomRef.current;

    // 3. Renderer setup
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mountPoint.appendChild(renderer.domElement);

    // 4. Lights
    const ambientLight = new THREE.AmbientLight(0xffffff, 0.3);
    scene.add(ambientLight);

    const pointLight = new THREE.PointLight(0x00f2ff, 1, 100);
    pointLight.position.set(0, 0, 10);
    scene.add(pointLight);

    const secondaryLight = new THREE.PointLight(0x7c3aed, 0.8, 100);
    secondaryLight.position.set(5, 5, -5);
    scene.add(secondaryLight);

    // Group to hold all graph objects
    const graphGroup = new THREE.Group();
    scene.add(graphGroup);

    // Node geometries and materials
    const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
    const hexCylinderGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.04, 6);
    hexCylinderGeo.rotateX(Math.PI / 2); // Orient hexagon to face front

    // Helper to generate materials
    const createNodeMaterial = (color: number, opacity = 1.0) => {
      return new THREE.MeshPhongMaterial({
        color,
        emissive: color,
        emissiveIntensity: 0.25,
        transparent: true,
        opacity,
        shininess: 30,
      });
    };

    // Keep track of active nodes and edges in threejs
    const threeNodesMap = new Map<string, NodeState>();
    const threeEdgesList: { source: string; target: string; line: THREE.Line }[] = [];

    // Raycaster for mouse hovering
    const raycaster = new THREE.Raycaster();
    const ndcMouse = new THREE.Vector2();

    // Synchronization of nodes from props
    const syncNodesAndEdges = () => {
      // Clean up deleted nodes
      const currentIds = new Set(nodes.map(n => n.id));
      for (const [id, state] of threeNodesMap.entries()) {
        if (!currentIds.has(id)) {
          // Fade node out, then delete it when opacity is low
          state.targetOpacity = 0.0;
          state.targetScale = 0.0;
        }
      }

      // Add or update nodes
      for (const node of nodes) {
        const isConcept = node.source === 'sleep' || conceptsRef.current.has(node.content);
        const isActivated = activatedRef.current.has(node.id);
        const isFaded = fadedRef.current.has(node.id);

        let colorVal = 0x3b82f6; // Episodic Blue
        if (isConcept) colorVal = 0x7c3aed; // Concept Violet
        if (isActivated) colorVal = 0x00e5c7; // Activated Cyan
        if (isFaded) colorVal = 0x475569; // Pruned Grey

        const [hx, hy, hz] = hashPosition3D(node.id);
        let tx = hx;
        let ty = hy;
        let tz = hz;

        // Pull toward cluster center if applicable
        const clusterCenter = nodeToClusterCenterRef.current.get(node.id);
        if (clusterCenter) {
          tx = clusterCenter[0] + (hx - clusterCenter[0]) * 0.3;
          ty = clusterCenter[1] + (hy - clusterCenter[1]) * 0.3;
          tz = clusterCenter[2] + (hz - clusterCenter[2]) * 0.3;
        }

        const targetPos = new THREE.Vector3(tx, ty, tz);
        let targetScale = isConcept ? 1.2 : 1.0;
        if (isActivated) targetScale *= 1.35;
        if (isFaded) targetScale *= 0.6;

        let targetOpacity = isFaded ? 0.3 : 1.0;

        if (threeNodesMap.has(node.id)) {
          const state = threeNodesMap.get(node.id)!;
          state.targetPos.copy(targetPos);
          state.targetScale = targetScale;
          state.targetOpacity = targetOpacity;
          state.targetColor.setHex(colorVal);
          state.data = node;
        } else {
          // Create new mesh
          const mat = createNodeMaterial(colorVal, 0.0); // Start transparent
          const mesh = new THREE.Mesh(isConcept ? hexCylinderGeo : sphereGeo, mat);
          mesh.position.set(hx, hy, hz);
          mesh.scale.set(0.01, 0.01, 0.01); // Start small
          graphGroup.add(mesh);

          threeNodesMap.set(node.id, {
            id: node.id,
            mesh,
            targetPos,
            targetScale,
            targetColor: new THREE.Color(colorVal),
            targetOpacity,
            data: node,
            isConcept,
            position: new THREE.Vector3(hx, hy, hz),
            velocity: new THREE.Vector3(0, 0, 0),
            force: new THREE.Vector3(0, 0, 0),
          });
        }
      }

      // Synchronize edges
      // Clean old lines
      threeEdgesList.forEach(e => graphGroup.remove(e.line));
      threeEdgesList.length = 0;

      // Add new edges
      for (const edge of edges) {
        const srcState = threeNodesMap.get(edge.source);
        const tgtState = threeNodesMap.get(edge.target);
        if (!srcState || !tgtState) continue;

        const lineMat = new THREE.LineBasicMaterial({
          color: edge.type === 'ABSTRACTED_BY' ? 0x7c3aed : 0x3b82f6,
          transparent: true,
          opacity: 0.0, // Start transparent
        });

        const points = [srcState.mesh.position, tgtState.mesh.position];
        const lineGeo = new THREE.BufferGeometry().setFromPoints(points);
        const line = new THREE.Line(lineGeo, lineMat);
        graphGroup.add(line);

        threeEdgesList.push({
          source: edge.source,
          target: edge.target,
          line,
        });
      }

      nodesMapRef.current = threeNodesMap;
      edgesListRef.current = threeEdgesList;
    };

    // Run initial sync
    syncNodesAndEdges();

    // Resize observer
    const handleResize = () => {
      const w = mountPoint.clientWidth;
      const h = mountPoint.clientHeight;
      camera.aspect = w / h;
      camera.updateProjectionMatrix();
      renderer.setSize(w, h);
    };

    const resizeObserver = new ResizeObserver(handleResize);
    resizeObserver.observe(mountPoint);

    // Mouse listener handlers inside the container
    let isMouseDown = false;
    let previousMousePosition = { x: 0, y: 0 };

    const handleMouseDown = (e: MouseEvent) => {
      isMouseDown = true;
      isDraggingRef.current = false;
      previousMousePosition = { x: e.clientX, y: e.clientY };
    };

    const handleMouseMove = (e: MouseEvent) => {
      // Calculate normalized device coordinates (-1 to +1) for raycasting
      const rect = renderer.domElement.getBoundingClientRect();
      ndcMouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      ndcMouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;

      if (isMouseDown) {
        const deltaMove = {
          x: e.clientX - previousMousePosition.x,
          y: e.clientY - previousMousePosition.y,
        };

        if (Math.abs(deltaMove.x) > 2 || Math.abs(deltaMove.y) > 2) {
          isDraggingRef.current = true;
        }

        targetRotationRef.current.y += deltaMove.x * 0.005;
        targetRotationRef.current.x += deltaMove.y * 0.005;

        previousMousePosition = { x: e.clientX, y: e.clientY };
      }
    };

    const handleMouseUp = () => {
      isMouseDown = false;
    };

    const handleWheel = (e: WheelEvent) => {
      e.preventDefault();
      zoomRef.current = Math.max(3.0, Math.min(15.0, zoomRef.current + e.deltaY * 0.005));
    };

    mountPoint.addEventListener('mousedown', handleMouseDown);
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    mountPoint.addEventListener('wheel', handleWheel, { passive: false });

    // 5. Animation Frame Loop
    let animId: number;

    const tick = () => {
      // Smoothly rotate the scene toward drag targets
      rotationRef.current.x += (targetRotationRef.current.x - rotationRef.current.x) * 0.1;
      rotationRef.current.y += (targetRotationRef.current.y - rotationRef.current.y) * 0.1;

      // Add a tiny, subtle ambient rotation if the user isn't dragging
      if (!isMouseDown) {
        targetRotationRef.current.y += 0.0006;
      }

      graphGroup.rotation.x = rotationRef.current.x;
      graphGroup.rotation.y = rotationRef.current.y;

      // Smoothly zoom camera
      camera.position.z += (zoomRef.current - camera.position.z) * 0.1;

      // --- Dynamic 3D Force-Directed Layout Physics Engine ---
      const dt = 0.08;
      const k_repel = 0.15;
      const k_attract = 0.25;
      const rest_length = 1.0;
      const k_gravity = 0.04;
      const damping = 0.85;

      // 1. Reset forces
      threeNodesMap.forEach((u) => {
        u.force.set(0, 0, 0);
      });

      // 2. Repulsion (charge) forces between all node pairs
      const nodesList = Array.from(threeNodesMap.values()).filter(u => u.targetOpacity > 0.0);
      for (let i = 0; i < nodesList.length; i++) {
        const u = nodesList[i];
        for (let j = i + 1; j < nodesList.length; j++) {
          const v = nodesList[j];
          const dir = new THREE.Vector3().subVectors(u.position, v.position);
          let dist = dir.length();
          if (dist < 0.1) {
            dir.set(Math.random() - 0.5, Math.random() - 0.5, Math.random() - 0.5).normalize();
            dist = 0.1;
          }
          const f_mag = k_repel / (dist * dist);
          const forceVec = dir.normalize().multiplyScalar(f_mag);
          u.force.add(forceVec);
          v.force.sub(forceVec);
        }
      }

      // 3. Attraction (spring) forces along active edges
      threeEdgesList.forEach(edge => {
        const u = threeNodesMap.get(edge.source);
        const v = threeNodesMap.get(edge.target);
        if (!u || !v || u.targetOpacity === 0.0 || v.targetOpacity === 0.0) return;

        const dir = new THREE.Vector3().subVectors(v.position, u.position);
        let dist = dir.length();
        if (dist < 0.1) dist = 0.1;
        const f_mag = k_attract * (dist - rest_length);
        const forceVec = dir.normalize().multiplyScalar(f_mag);
        u.force.add(forceVec);
        v.force.sub(forceVec);
      });

      // 4. Center attraction / gravity and velocity integration
      threeNodesMap.forEach((u) => {
        // Gravity
        const gravityForce = u.position.clone().multiplyScalar(-k_gravity);
        u.force.add(gravityForce);

        // Pull to target hash coordinates to anchor visual zones
        const pullForce = new THREE.Vector3().subVectors(u.targetPos, u.position).multiplyScalar(0.08);
        u.force.add(pullForce);

        // Integrate
        u.velocity.add(u.force.multiplyScalar(dt));
        u.velocity.multiplyScalar(damping);
        u.position.add(u.velocity.clone().multiplyScalar(dt));

        // Lerp mesh position to physics position
        u.mesh.position.lerp(u.position, 0.15);
      });

      // Update scale and material parameters for nodes
      threeNodesMap.forEach((state, id) => {
        // Lerp scale
        const currentScale = state.mesh.scale.x;
        const nextScale = currentScale + (state.targetScale - currentScale) * 0.08;
        state.mesh.scale.set(nextScale, nextScale, nextScale);

        // Lerp material values
        const mat = state.mesh.material as THREE.MeshPhongMaterial;
        mat.opacity += (state.targetOpacity - mat.opacity) * 0.08;
        mat.color.lerp(state.targetColor, 0.08);
        mat.emissive.copy(mat.color);

        // Remove node from group completely if it is collapsed
        if (state.targetOpacity === 0.0 && mat.opacity < 0.05) {
          graphGroup.remove(state.mesh);
          threeNodesMap.delete(id);
        }
      });

      // Update line connections
      threeEdgesList.forEach(edge => {
        const src = threeNodesMap.get(edge.source);
        const tgt = threeNodesMap.get(edge.target);
        if (!src || !tgt) return;

        const positions = edge.line.geometry.attributes.position;
        const posArray = positions.array as Float32Array;

        // Set point 1 (source)
        posArray[0] = src.mesh.position.x;
        posArray[1] = src.mesh.position.y;
        posArray[2] = src.mesh.position.z;

        // Set point 2 (target)
        posArray[3] = tgt.mesh.position.x;
        posArray[4] = tgt.mesh.position.y;
        posArray[5] = tgt.mesh.position.z;

        positions.needsUpdate = true;

        // Fade in line opacity relative to the nodes' opacities
        const targetLineOpacity = Math.min(
          (src.mesh.material as THREE.MeshPhongMaterial).opacity,
          (tgt.mesh.material as THREE.MeshPhongMaterial).opacity
        ) * 0.3;
        const lineMat = edge.line.material as THREE.LineBasicMaterial;
        lineMat.opacity += (targetLineOpacity - lineMat.opacity) * 0.1;
      });

      // Raycast hovering
      raycaster.setFromCamera(ndcMouse, camera);
      const intersects = raycaster.intersectObjects(
        Array.from(threeNodesMap.values()).map(n => n.mesh)
      );

      if (intersects.length > 0) {
        const hoveredMesh = intersects[0].object as THREE.Mesh;
        // Find state
        let foundNode: NodeState | null = null;
        for (const state of threeNodesMap.values()) {
          if (state.mesh === hoveredMesh) {
            foundNode = state;
            break;
          }
        }
        if (foundNode) {
          setHoveredNode(foundNode.data);
          // Calculate screen tooltip position
          const vec = foundNode.mesh.position.clone().project(camera);
          const x = (vec.x * .5 + .5) * width;
          const y = (-(vec.y * .5) + .5) * height;
          setTooltipPos({ x, y });
        }
      } else {
        setHoveredNode(null);
      }

      renderer.render(scene, camera);
      animId = requestAnimationFrame(tick);
    };

    animId = requestAnimationFrame(tick);

    // Clean up function
    return () => {
      cancelAnimationFrame(animId);
      resizeObserver.disconnect();
      mountPoint.removeEventListener('mousedown', handleMouseDown);
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
      mountPoint.removeEventListener('wheel', handleWheel);

      // Dispose elements
      threeNodesMap.forEach(n => {
        n.mesh.geometry.dispose();
        (n.mesh.material as THREE.Material).dispose();
      });
      threeEdgesList.forEach(e => {
        e.line.geometry.dispose();
        (e.line.material as THREE.Material).dispose();
      });
      sphereGeo.dispose();
      hexCylinderGeo.dispose();
      renderer.dispose();
      if (mountPoint.contains(renderer.domElement)) {
        mountPoint.removeChild(renderer.domElement);
      }
    };
  }, [nodes, edges]);

  // Click selection
  const handleClick = useCallback(() => {
    if (hoveredNode && !isDraggingRef.current) {
      onNodeClick(hoveredNode);
    }
  }, [hoveredNode, onNodeClick]);

  return (
    <div className="panel graph-viewport" ref={containerRef}>
      <div className="panel-header">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="4" cy="4" r="2" stroke="currentColor" strokeWidth="1.2" />
          <circle cx="10" cy="10" r="2" stroke="currentColor" strokeWidth="1.2" />
          <line x1="5.5" y1="5.5" x2="8.5" y2="8.5" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        Memory Graph
        <span className="graph-viewport__count">{nodes.length} nodes · {edges.length} edges</span>
      </div>
      <div className="graph-viewport__canvas-wrap" style={{ cursor: hoveredNode ? 'pointer' : 'grab' }}>
        <div
          ref={mountRef}
          className="graph-viewport__canvas"
          onClick={handleClick}
        />
        {hoveredNode && (
          <div
            className="graph-viewport__tooltip"
            style={{
              left: tooltipPos.x + 12,
              top: tooltipPos.y - 8,
              position: 'absolute',
              pointerEvents: 'none',
            }}
          >
            <span className="graph-viewport__tooltip-id">{hoveredNode.id}</span>
            <p>{hoveredNode.content}</p>
            {hoveredNode.semantic_tags && hoveredNode.semantic_tags.length > 0 && (
              <div className="graph-viewport__tooltip-tags">
                {hoveredNode.semantic_tags.map(t => (
                  <span key={t} className="graph-viewport__tag">{t}</span>
                ))}
              </div>
            )}
          </div>
        )}
      </div>
      <div className="graph-viewport__legend">
        <span className="graph-viewport__legend-item">
          <span className="graph-viewport__legend-dot" style={{ background: '#3b82f6' }} />
          Episodic
        </span>
        <span className="graph-viewport__legend-item">
          <span className="graph-viewport__legend-hex" />
          Concept
        </span>
        <span className="graph-viewport__legend-item">
          <span className="graph-viewport__legend-dot" style={{ background: '#00e5c7' }} />
          Activated
        </span>
        <span className="graph-viewport__legend-item">
          <span className="graph-viewport__legend-dot" style={{ background: '#475569', opacity: 0.4 }} />
          Pruned
        </span>
      </div>
    </div>
  );
}
