import { useRef, useEffect, useCallback, useState } from 'react';
import * as THREE from 'three';
import type { MemoryNode, MemoryEdge, VisEvent } from '../types';
import './GraphViewport.css';

interface GraphViewportProps {
  nodes: MemoryNode[];
  edges: MemoryEdge[];
  events: VisEvent[];
  onNodeClick: (node: MemoryNode) => void;
  onDeleteNode?: (nodeId: string) => void;
  onDeleteAll?: () => void;
}

// Stable hash-based position — internal only, never shown
function hashPosition3D(id: string): [number, number, number] {
  let h1 = 0, h2 = 0, h3 = 0;
  for (let i = 0; i < id.length; i++) {
    h1 = ((h1 << 5) - h1 + id.charCodeAt(i)) | 0;
    h2 = ((h2 << 7) - h2 + id.charCodeAt(i)) | 0;
    h3 = ((h3 << 3) - h3 + id.charCodeAt(i)) | 0;
  }
  return [(Math.abs(h1 % 600) / 100) - 3, (Math.abs(h2 % 400) / 100) - 2, (Math.abs(h3 % 400) / 100) - 2];
}

function hashPosition2D(id: string, w: number, h: number): [number, number] {
  let h1 = 0, h2 = 0;
  for (let i = 0; i < id.length; i++) {
    h1 = ((h1 << 5) - h1 + id.charCodeAt(i)) | 0;
    h2 = ((h2 << 7) - h2 + id.charCodeAt(i)) | 0;
  }
  const margin = 80;
  return [margin + (Math.abs(h1) % (w - margin * 2)), margin + (Math.abs(h2) % (h - margin * 2))];
}

function getNodeColor(node: MemoryNode, isConcept: boolean, isActivated: boolean, isFaded: boolean): number {
  const status = node.metadata?.status as string | undefined;
  if (status === 'SUPERSEDED') return 0x8b2525;
  if (status === 'ARCHIVED')   return 0x3a3a42;
  if (isFaded)                  return 0x4a4a54;
  if (isActivated)              return 0x6baf7a;
  if (isConcept)                return 0xe8a43a;
  return 0x5b9bd5;
}

function hexToRgb(hex: number): string {
  return `rgb(${(hex >> 16) & 0xff},${(hex >> 8) & 0xff},${hex & 0xff})`;
}

// Show real content, never hashes
function nodeLabel(node: MemoryNode): string {
  const c = node.content?.trim() || '';
  return c.length > 24 ? c.slice(0, 22) + '…' : c || '(empty)';
}

// ─────────────────────────────────────────────
//  2D CANVAS VIEW
// ─────────────────────────────────────────────
interface Node2D {
  id: string; data: MemoryNode;
  x: number; y: number; vx: number; vy: number; fx: number; fy: number;
  isConcept: boolean; isActivated: boolean; isFaded: boolean;
  color: number; radius: number;
  targetOpacity: number; opacity: number;
}

function GraphViewport2D({ nodes, edges, events, onNodeClick, onDeleteNode }: GraphViewportProps) {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const nodesRef = useRef<Map<string, Node2D>>(new Map());
  const animIdRef = useRef<number>(0);
  const mouseRef = useRef({ x: -9999, y: -9999, inside: false });
  const [hoveredNode, setHoveredNode] = useState<MemoryNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const activatedRef = useRef<Set<string>>(new Set());
  const fadedRef = useRef<Set<string>>(new Set());
  const conceptsRef = useRef<Set<string>>(new Set());

  useEffect(() => {
    for (const evt of events) {
      if (evt.type === 'node_activate') evt.node_ids?.forEach(id => activatedRef.current.add(id));
      if (evt.type === 'node_fade' || evt.type === 'node_merge') evt.node_ids?.forEach(id => fadedRef.current.add(id));
      if (evt.type === 'concept_create' && evt.concept_label) conceptsRef.current.add(evt.concept_label);
    }
  }, [events]);

  useEffect(() => {
    const canvas = canvasRef.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d')!;
    let dpr = window.devicePixelRatio || 1;

    const resize = () => {
      dpr = window.devicePixelRatio || 1;
      canvas.width = canvas.offsetWidth * dpr;
      canvas.height = canvas.offsetHeight * dpr;
      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    };
    resize();
    const ro = new ResizeObserver(resize);
    ro.observe(canvas);

    const lerp = (a: number, b: number, t: number) => a + (b - a) * t;

    const tick = () => {
      const w = canvas.offsetWidth;
      const h = canvas.offsetHeight;

      // Sync node map with current props
      const currentIds = new Set(nodes.map(n => n.id));
      for (const [id] of nodesRef.current) {
        if (!currentIds.has(id)) nodesRef.current.delete(id);
      }
      for (const node of nodes) {
        const isConcept = node.source === 'sleep' || conceptsRef.current.has(node.content);
        const isActivated = activatedRef.current.has(node.id);
        const isFaded = fadedRef.current.has(node.id);
        const color = getNodeColor(node, isConcept, isActivated, isFaded);
        const radius = isConcept ? 14 : isActivated ? 12 : 9;
        if (!nodesRef.current.has(node.id)) {
          const [sx, sy] = hashPosition2D(node.id, w || 600, h || 400);
          nodesRef.current.set(node.id, { id: node.id, data: node, x: sx, y: sy, vx: 0, vy: 0, fx: 0, fy: 0, isConcept, isActivated, isFaded, color, radius, targetOpacity: isFaded ? 0.35 : 1.0, opacity: 0.0 });
        } else {
          const n = nodesRef.current.get(node.id)!;
          Object.assign(n, { data: node, isConcept, isActivated, isFaded, color, radius, targetOpacity: isFaded ? 0.35 : 1.0 });
        }
      }

      ctx.clearRect(0, 0, w, h);
      const nodeList = Array.from(nodesRef.current.values());

      // Force-directed physics
      const K_REPEL = 2800, K_SPRING = 0.035, REST = 140, GRAVITY = 0.018, DAMP = 0.78;
      nodeList.forEach(n => { n.fx = 0; n.fy = 0; });

      for (let i = 0; i < nodeList.length; i++) {
        for (let j = i + 1; j < nodeList.length; j++) {
          const a = nodeList[i], b = nodeList[j];
          const dx = a.x - b.x, dy = a.y - b.y;
          const dist = Math.sqrt(dx * dx + dy * dy) || 0.1;
          const f = K_REPEL / (dist * dist);
          a.fx += (dx / dist) * f; a.fy += (dy / dist) * f;
          b.fx -= (dx / dist) * f; b.fy -= (dy / dist) * f;
        }
      }
      for (const edge of edges) {
        const a = nodesRef.current.get(edge.source), b = nodesRef.current.get(edge.target);
        if (!a || !b) continue;
        const dx = b.x - a.x, dy = b.y - a.y;
        const dist = Math.sqrt(dx * dx + dy * dy) || 0.1;
        const f = K_SPRING * (dist - REST);
        a.fx += (dx / dist) * f; a.fy += (dy / dist) * f;
        b.fx -= (dx / dist) * f; b.fy -= (dy / dist) * f;
      }
      nodeList.forEach(n => {
        n.fx += (w / 2 - n.x) * GRAVITY;
        n.fy += (h / 2 - n.y) * GRAVITY;
        n.vx = (n.vx + n.fx * 0.1) * DAMP;
        n.vy = (n.vy + n.fy * 0.1) * DAMP;
        n.x = Math.max(n.radius + 6, Math.min(w - n.radius - 6, n.x + n.vx));
        n.y = Math.max(n.radius + 6, Math.min(h - n.radius - 6, n.y + n.vy));
        n.opacity = lerp(n.opacity, n.targetOpacity, 0.06);
      });

      // Draw edges
      for (const edge of edges) {
        const a = nodesRef.current.get(edge.source), b = nodesRef.current.get(edge.target);
        if (!a || !b) continue;
        ctx.globalAlpha = Math.min(a.opacity, b.opacity) * 0.35;
        ctx.strokeStyle = edge.type === 'ABSTRACTED_BY' ? '#e8a43a' : edge.type === 'SUPERSEDED_BY' ? '#d9534f' : '#5b9bd5';
        ctx.lineWidth = 1;
        ctx.beginPath(); ctx.moveTo(a.x, a.y); ctx.lineTo(b.x, b.y); ctx.stroke();
      }
      ctx.globalAlpha = 1;

      // Hover detection (pure geometry, no setState in loop)
      const mx = mouseRef.current.x, my = mouseRef.current.y;
      let hoveredThisFrame: MemoryNode | null = null;

      // Draw nodes
      nodeList.forEach(n => {
        const rgb = hexToRgb(n.color);
        ctx.globalAlpha = n.opacity;

        // Glow halo
        const grd = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, n.radius * 2.5);
        const [r, g, b] = [n.color >> 16 & 0xff, n.color >> 8 & 0xff, n.color & 0xff];
        grd.addColorStop(0, `rgba(${r},${g},${b},0.18)`);
        grd.addColorStop(1, 'rgba(0,0,0,0)');
        ctx.beginPath(); ctx.arc(n.x, n.y, n.radius * 2.5, 0, Math.PI * 2);
        ctx.fillStyle = grd; ctx.fill();

        // Shape
        if (n.isConcept) {
          ctx.beginPath();
          for (let i = 0; i < 6; i++) {
            const a = (Math.PI / 3) * i - Math.PI / 6;
            const px = n.x + n.radius * Math.cos(a), py = n.y + n.radius * Math.sin(a);
            i === 0 ? ctx.moveTo(px, py) : ctx.lineTo(px, py);
          }
          ctx.closePath();
          ctx.fillStyle = rgb; ctx.fill();
          ctx.globalAlpha = n.opacity * 0.35;
          ctx.strokeStyle = '#fff'; ctx.lineWidth = 1.5; ctx.stroke();
        } else {
          ctx.beginPath(); ctx.arc(n.x, n.y, n.radius, 0, Math.PI * 2);
          ctx.fillStyle = rgb; ctx.fill();
          ctx.globalAlpha = n.opacity * 0.2;
          ctx.strokeStyle = '#fff'; ctx.lineWidth = 1; ctx.stroke();
        }
        ctx.globalAlpha = n.opacity;

        // Hover check
        if (mouseRef.current.inside) {
          const dx = mx - n.x, dy = my - n.y;
          if (Math.sqrt(dx * dx + dy * dy) < n.radius + 5) hoveredThisFrame = n.data;
        }
      });

      ctx.globalAlpha = 1;
      setHoveredNode(prev => {
        if (prev?.id !== hoveredThisFrame?.id) return hoveredThisFrame;
        return prev;
      });
      if (hoveredThisFrame) setTooltipPos({ x: mx, y: my });

      animIdRef.current = requestAnimationFrame(tick);
    };

    animIdRef.current = requestAnimationFrame(tick);

    const onMouseMove = (e: MouseEvent) => {
      const rect = canvas.getBoundingClientRect();
      mouseRef.current = { x: e.clientX - rect.left, y: e.clientY - rect.top, inside: true };
    };
    const onMouseLeave = () => {
      mouseRef.current = { x: -9999, y: -9999, inside: false };
      setHoveredNode(null);
    };
    canvas.addEventListener('mousemove', onMouseMove);
    canvas.addEventListener('mouseleave', onMouseLeave);

    return () => {
      cancelAnimationFrame(animIdRef.current);
      ro.disconnect();
      canvas.removeEventListener('mousemove', onMouseMove);
      canvas.removeEventListener('mouseleave', onMouseLeave);
    };
  }, [nodes, edges]);

  const handleClick = useCallback(() => {
    if (hoveredNode) onNodeClick(hoveredNode);
  }, [hoveredNode, onNodeClick]);

  return (
    <div className="graph-viewport__canvas-wrap" style={{ cursor: hoveredNode ? 'pointer' : 'default' }}>
      <canvas ref={canvasRef} className="graph-viewport__canvas graph-viewport__canvas--2d" onClick={handleClick} />

      {/* Tooltip — only shows when hovering a node, clears on mouseleave */}
      {hoveredNode && (
        <div className="graph-viewport__tooltip" style={{ left: tooltipPos.x + 14, top: tooltipPos.y - 8, position: 'absolute', pointerEvents: 'none' }}>
          <span className="graph-viewport__tooltip-source">{hoveredNode.source}</span>
          <p>{hoveredNode.content}</p>
          {hoveredNode.semantic_tags?.length > 0 && (
            <div className="graph-viewport__tooltip-tags">
              {hoveredNode.semantic_tags.map(t => <span key={t} className="graph-viewport__tag">{t}</span>)}
            </div>
          )}
          {onDeleteNode && (
            <button
              className="graph-viewport__tooltip-delete"
              onPointerDown={e => { e.stopPropagation(); setConfirmDelete(hoveredNode.id); }}
            >
              🗑 Delete this memory
            </button>
          )}
        </div>
      )}

      {/* Confirm delete dialog */}
      {confirmDelete && (
        <div className="graph-viewport__confirm">
          <p>Delete this memory node?</p>
          <div className="graph-viewport__confirm-btns">
            <button className="btn-danger-sm" onClick={() => { onDeleteNode?.(confirmDelete); setConfirmDelete(null); setHoveredNode(null); }}>Delete</button>
            <button className="btn-ghost-sm" onClick={() => setConfirmDelete(null)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  3D THREE.JS VIEW
// ─────────────────────────────────────────────
interface NodeState3D {
  id: string; mesh: THREE.Mesh; targetPos: THREE.Vector3;
  targetScale: number; targetColor: THREE.Color; targetOpacity: number;
  data: MemoryNode; isConcept: boolean; position: THREE.Vector3;
  velocity: THREE.Vector3; force: THREE.Vector3;
}

function GraphViewport3D({ nodes, edges, events, onNodeClick, onDeleteNode }: GraphViewportProps) {
  const mountRef = useRef<HTMLDivElement>(null);
  const [hoveredNode, setHoveredNode] = useState<MemoryNode | null>(null);
  const [tooltipPos, setTooltipPos] = useState({ x: 0, y: 0 });
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null);

  const activatedRef = useRef<Set<string>>(new Set());
  const fadedRef = useRef<Set<string>>(new Set());
  const conceptsRef = useRef<Set<string>>(new Set());
  const clusterCentersRef = useRef<Map<number, [number, number, number]>>(new Map());
  const nodeToClusterCenterRef = useRef<Map<string, [number, number, number]>>(new Map());
  const isDraggingRef = useRef<boolean>(false);
  const rotationRef = useRef({ x: 0, y: 0 });
  const targetRotationRef = useRef({ x: 0, y: 0 });
  const zoomRef = useRef<number>(6.5);

  useEffect(() => {
    for (const evt of events) {
      if (evt.type === 'node_activate') evt.node_ids?.forEach(id => activatedRef.current.add(id));
      if (evt.type === 'node_fade' || evt.type === 'node_merge') evt.node_ids?.forEach(id => fadedRef.current.add(id));
      if (evt.type === 'concept_create' && evt.concept_label) conceptsRef.current.add(evt.concept_label);
      if (evt.type === 'cluster_form' && evt.cluster_id !== undefined && evt.cluster_members) {
        const members = evt.cluster_members;
        let cx = 0, cy = 0, cz = 0;
        for (const mid of members) { const p = hashPosition3D(mid); cx += p[0]; cy += p[1]; cz += p[2]; }
        const center = [cx / members.length, cy / members.length, cz / members.length] as [number, number, number];
        clusterCentersRef.current.set(evt.cluster_id, center);
        members.forEach(mid => nodeToClusterCenterRef.current.set(mid, center));
      }
    }
  }, [events]);

  useEffect(() => {
    const mountPoint = mountRef.current;
    if (!mountPoint) return;
    const width = mountPoint.clientWidth || 600;
    const height = mountPoint.clientHeight || 400;

    const scene = new THREE.Scene();
    const camera = new THREE.PerspectiveCamera(60, width / height, 0.1, 1000);
    camera.position.z = zoomRef.current;
    const renderer = new THREE.WebGLRenderer({ alpha: true, antialias: true });
    renderer.setSize(width, height);
    renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
    mountPoint.appendChild(renderer.domElement);

    scene.add(new THREE.AmbientLight(0xfff5e6, 0.35));
    const pl1 = new THREE.PointLight(0xe8a43a, 0.9, 100); pl1.position.set(0, 0, 10); scene.add(pl1);
    const pl2 = new THREE.PointLight(0x5b9bd5, 0.6, 100); pl2.position.set(5, 5, -5); scene.add(pl2);

    const graphGroup = new THREE.Group(); scene.add(graphGroup);
    const sphereGeo = new THREE.SphereGeometry(0.12, 16, 16);
    const hexGeo = new THREE.CylinderGeometry(0.18, 0.18, 0.04, 6);
    hexGeo.rotateX(Math.PI / 2);

    const mkMat = (color: number, opacity = 1.0) => new THREE.MeshPhongMaterial({ color, emissive: color, emissiveIntensity: 0.25, transparent: true, opacity, shininess: 30 });

    const threeNodes = new Map<string, NodeState3D>();
    const threeEdges: { source: string; target: string; line: THREE.Line }[] = [];
    const raycaster = new THREE.Raycaster();
    const ndcMouse = new THREE.Vector2();

    const syncAll = () => {
      const currentIds = new Set(nodes.map(n => n.id));
      for (const [id, s] of threeNodes.entries()) {
        if (!currentIds.has(id)) { s.targetOpacity = 0; s.targetScale = 0; }
      }
      for (const node of nodes) {
        const isConcept = node.source === 'sleep' || conceptsRef.current.has(node.content);
        const isActivated = activatedRef.current.has(node.id);
        const isFaded = fadedRef.current.has(node.id);
        const colorVal = getNodeColor(node, isConcept, isActivated, isFaded);
        const [hx, hy, hz] = hashPosition3D(node.id);
        const cc = nodeToClusterCenterRef.current.get(node.id);
        const tx = cc ? cc[0] + (hx - cc[0]) * 0.3 : hx;
        const ty = cc ? cc[1] + (hy - cc[1]) * 0.3 : hy;
        const tz = cc ? cc[2] + (hz - cc[2]) * 0.3 : hz;
        const targetPos = new THREE.Vector3(tx, ty, tz);
        const status = node.metadata?.status as string | undefined;
        let ts = isConcept ? 1.2 : 1.0;
        if (isActivated) ts *= 1.35; if (isFaded) ts *= 0.6;
        if (status === 'SUPERSEDED') ts *= 0.85; if (status === 'ARCHIVED') ts *= 0.7;
        let to = isFaded ? 0.3 : 1.0;
        if (status === 'SUPERSEDED') to = 0.55; if (status === 'ARCHIVED') to = 0.3;

        if (threeNodes.has(node.id)) {
          const s = threeNodes.get(node.id)!;
          s.targetPos.copy(targetPos); s.targetScale = ts; s.targetOpacity = to;
          s.targetColor.setHex(colorVal); s.data = node;
        } else {
          const mat = mkMat(colorVal, 0);
          const mesh = new THREE.Mesh(isConcept ? hexGeo : sphereGeo, mat);
          mesh.position.set(hx, hy, hz); mesh.scale.set(0.01, 0.01, 0.01);
          graphGroup.add(mesh);
          threeNodes.set(node.id, { id: node.id, mesh, targetPos, targetScale: ts, targetColor: new THREE.Color(colorVal), targetOpacity: to, data: node, isConcept, position: new THREE.Vector3(hx, hy, hz), velocity: new THREE.Vector3(), force: new THREE.Vector3() });
        }
      }
      threeEdges.forEach(e => graphGroup.remove(e.line)); threeEdges.length = 0;
      for (const edge of edges) {
        const src = threeNodes.get(edge.source), tgt = threeNodes.get(edge.target);
        if (!src || !tgt) continue;
        const ec = edge.type === 'ABSTRACTED_BY' ? 0xe8a43a : edge.type === 'SUPERSEDED_BY' ? 0xd9534f : 0x5b9bd5;
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([src.mesh.position, tgt.mesh.position]), new THREE.LineBasicMaterial({ color: ec, transparent: true, opacity: 0 }));
        graphGroup.add(line); threeEdges.push({ source: edge.source, target: edge.target, line });
      }
    };
    syncAll();

    const ro = new ResizeObserver(() => {
      const w = mountPoint.clientWidth, h = mountPoint.clientHeight;
      camera.aspect = w / h; camera.updateProjectionMatrix(); renderer.setSize(w, h);
    });
    ro.observe(mountPoint);

    let isMouseDown = false, prev = { x: 0, y: 0 };
    const onMouseDown = (e: MouseEvent) => { isMouseDown = true; isDraggingRef.current = false; prev = { x: e.clientX, y: e.clientY }; };
    const onMouseMove = (e: MouseEvent) => {
      const rect = renderer.domElement.getBoundingClientRect();
      ndcMouse.x = ((e.clientX - rect.left) / rect.width) * 2 - 1;
      ndcMouse.y = -((e.clientY - rect.top) / rect.height) * 2 + 1;
      if (isMouseDown) {
        const dx = e.clientX - prev.x, dy = e.clientY - prev.y;
        if (Math.abs(dx) > 2 || Math.abs(dy) > 2) isDraggingRef.current = true;
        targetRotationRef.current.y += dx * 0.005;
        targetRotationRef.current.x += dy * 0.005;
        prev = { x: e.clientX, y: e.clientY };
      }
    };
    const onMouseUp = () => { isMouseDown = false; };
    const onWheel = (e: WheelEvent) => { e.preventDefault(); zoomRef.current = Math.max(3, Math.min(15, zoomRef.current + e.deltaY * 0.005)); };
    mountPoint.addEventListener('mousedown', onMouseDown);
    window.addEventListener('mousemove', onMouseMove);
    window.addEventListener('mouseup', onMouseUp);
    mountPoint.addEventListener('wheel', onWheel, { passive: false });

    let animId: number;
    const tick = () => {
      rotationRef.current.x += (targetRotationRef.current.x - rotationRef.current.x) * 0.1;
      rotationRef.current.y += (targetRotationRef.current.y - rotationRef.current.y) * 0.1;
      if (!isMouseDown) targetRotationRef.current.y += 0.0006;
      graphGroup.rotation.x = rotationRef.current.x;
      graphGroup.rotation.y = rotationRef.current.y;
      camera.position.z += (zoomRef.current - camera.position.z) * 0.1;

      const DT = 0.08;
      threeNodes.forEach(u => u.force.set(0, 0, 0));
      const nl = Array.from(threeNodes.values()).filter(u => u.targetOpacity > 0);
      for (let i = 0; i < nl.length; i++) {
        for (let j = i + 1; j < nl.length; j++) {
          const u = nl[i], v = nl[j];
          const dir = new THREE.Vector3().subVectors(u.position, v.position);
          let d = dir.length(); if (d < 0.1) { dir.randomDirection(); d = 0.1; }
          const fv = dir.normalize().multiplyScalar(0.15 / (d * d));
          u.force.add(fv); v.force.sub(fv);
        }
      }
      threeEdges.forEach(e => {
        const u = threeNodes.get(e.source), v = threeNodes.get(e.target);
        if (!u || !v || u.targetOpacity === 0 || v.targetOpacity === 0) return;
        const dir = new THREE.Vector3().subVectors(v.position, u.position);
        let d = dir.length(); if (d < 0.1) d = 0.1;
        const fv = dir.normalize().multiplyScalar(0.25 * (d - 1.0));
        u.force.add(fv); v.force.sub(fv);
      });
      threeNodes.forEach(u => {
        u.force.add(u.position.clone().multiplyScalar(-0.04));
        u.force.add(new THREE.Vector3().subVectors(u.targetPos, u.position).multiplyScalar(0.08));
        u.velocity.add(u.force.multiplyScalar(DT)); u.velocity.multiplyScalar(0.85);
        u.position.add(u.velocity.clone().multiplyScalar(DT));
        u.mesh.position.lerp(u.position, 0.15);
      });
      threeNodes.forEach((s, id) => {
        const cs = s.mesh.scale.x, ns = cs + (s.targetScale - cs) * 0.08;
        s.mesh.scale.set(ns, ns, ns);
        const mat = s.mesh.material as THREE.MeshPhongMaterial;
        mat.opacity += (s.targetOpacity - mat.opacity) * 0.08;
        mat.color.lerp(s.targetColor, 0.08); mat.emissive.copy(mat.color);
        if (s.targetOpacity === 0 && mat.opacity < 0.05) { graphGroup.remove(s.mesh); threeNodes.delete(id); }
      });
      threeEdges.forEach(e => {
        const src = threeNodes.get(e.source), tgt = threeNodes.get(e.target);
        if (!src || !tgt) return;
        const pa = e.line.geometry.attributes.position;
        const arr = pa.array as Float32Array;
        arr[0] = src.mesh.position.x; arr[1] = src.mesh.position.y; arr[2] = src.mesh.position.z;
        arr[3] = tgt.mesh.position.x; arr[4] = tgt.mesh.position.y; arr[5] = tgt.mesh.position.z;
        pa.needsUpdate = true;
        const to = Math.min((src.mesh.material as THREE.MeshPhongMaterial).opacity, (tgt.mesh.material as THREE.MeshPhongMaterial).opacity) * 0.3;
        (e.line.material as THREE.LineBasicMaterial).opacity += (to - (e.line.material as THREE.LineBasicMaterial).opacity) * 0.1;
      });
      raycaster.setFromCamera(ndcMouse, camera);
      const hits = raycaster.intersectObjects(Array.from(threeNodes.values()).map(n => n.mesh));
      if (hits.length > 0) {
        const hm = hits[0].object as THREE.Mesh;
        for (const s of threeNodes.values()) {
          if (s.mesh === hm) {
            setHoveredNode(s.data);
            const vec = s.mesh.position.clone().project(camera);
            setTooltipPos({ x: (vec.x * .5 + .5) * width, y: (-(vec.y * .5) + .5) * height });
            break;
          }
        }
      } else { setHoveredNode(null); }
      renderer.render(scene, camera); animId = requestAnimationFrame(tick);
    };
    animId = requestAnimationFrame(tick);

    return () => {
      cancelAnimationFrame(animId); ro.disconnect();
      mountPoint.removeEventListener('mousedown', onMouseDown);
      window.removeEventListener('mousemove', onMouseMove);
      window.removeEventListener('mouseup', onMouseUp);
      mountPoint.removeEventListener('wheel', onWheel);
      threeNodes.forEach(n => { n.mesh.geometry.dispose(); (n.mesh.material as THREE.Material).dispose(); });
      threeEdges.forEach(e => { e.line.geometry.dispose(); (e.line.material as THREE.Material).dispose(); });
      sphereGeo.dispose(); hexGeo.dispose(); renderer.dispose();
      if (mountPoint.contains(renderer.domElement)) mountPoint.removeChild(renderer.domElement);
    };
  }, [nodes, edges]);

  const handleClick = useCallback(() => {
    if (hoveredNode && !isDraggingRef.current) onNodeClick(hoveredNode);
  }, [hoveredNode, onNodeClick]);

  return (
    <div className="graph-viewport__canvas-wrap" style={{ cursor: hoveredNode ? 'pointer' : 'grab' }}>
      <div ref={mountRef} className="graph-viewport__canvas" onClick={handleClick} />
      {hoveredNode && (
        <div className="graph-viewport__tooltip" style={{ left: tooltipPos.x + 12, top: tooltipPos.y - 8, position: 'absolute', pointerEvents: 'none' }}>
          <span className="graph-viewport__tooltip-source">{hoveredNode.source}</span>
          <p>{hoveredNode.content}</p>
          {hoveredNode.semantic_tags?.length > 0 && (
            <div className="graph-viewport__tooltip-tags">
              {hoveredNode.semantic_tags.map(t => <span key={t} className="graph-viewport__tag">{t}</span>)}
            </div>
          )}
          {onDeleteNode && (
            <button className="graph-viewport__tooltip-delete" style={{ pointerEvents: 'auto' }} onClick={e => { e.stopPropagation(); setConfirmDelete(hoveredNode.id); }}>
              🗑 Delete this memory
            </button>
          )}
        </div>
      )}
      {confirmDelete && (
        <div className="graph-viewport__confirm">
          <p>Delete this memory node?</p>
          <div className="graph-viewport__confirm-btns">
            <button className="btn-danger-sm" onClick={() => { onDeleteNode?.(confirmDelete); setConfirmDelete(null); setHoveredNode(null); }}>Delete</button>
            <button className="btn-ghost-sm" onClick={() => setConfirmDelete(null)}>Cancel</button>
          </div>
        </div>
      )}
    </div>
  );
}

// ─────────────────────────────────────────────
//  MAIN EXPORT
// ─────────────────────────────────────────────
export function GraphViewport({ nodes, edges, events, onNodeClick, onDeleteNode, onDeleteAll }: GraphViewportProps) {
  const [is3D, setIs3D] = useState(true);
  const [confirmClearAll, setConfirmClearAll] = useState(false);

  return (
    <div className="panel graph-viewport">
      <div className="panel-header">
        <svg width="14" height="14" viewBox="0 0 14 14" fill="none">
          <circle cx="4" cy="4" r="2" stroke="currentColor" strokeWidth="1.2" />
          <circle cx="10" cy="10" r="2" stroke="currentColor" strokeWidth="1.2" />
          <line x1="5.5" y1="5.5" x2="8.5" y2="8.5" stroke="currentColor" strokeWidth="1.2" />
        </svg>
        Memory Graph
        <span className="graph-viewport__count">{nodes.length} nodes · {edges.length} edges</span>

        {/* 2D/3D Toggle */}
        <button id="graph-view-toggle" className="graph-viewport__view-toggle" onClick={() => setIs3D(v => !v)} title={is3D ? 'Switch to 2D' : 'Switch to 3D'}>
          <span className={`graph-viewport__toggle-opt ${!is3D ? 'active' : ''}`}>2D</span>
          <span className="graph-viewport__toggle-sep">|</span>
          <span className={`graph-viewport__toggle-opt ${is3D ? 'active' : ''}`}>3D</span>
        </button>

        {/* Clear All */}
        {onDeleteAll && nodes.length > 0 && (
          <button id="graph-clear-all" className="graph-viewport__clear-btn" onClick={() => setConfirmClearAll(true)} title="Clear all memories">
            🗑 Clear All
          </button>
        )}
      </div>

      {is3D
        ? <GraphViewport3D nodes={nodes} edges={edges} events={events} onNodeClick={onNodeClick} onDeleteNode={onDeleteNode} />
        : <GraphViewport2D nodes={nodes} edges={edges} events={events} onNodeClick={onNodeClick} onDeleteNode={onDeleteNode} />
      }

      {/* Confirm clear all overlay */}
      {confirmClearAll && (
        <div className="graph-viewport__overlay">
          <div className="graph-viewport__confirm graph-viewport__confirm--center">
            <p>⚠️ Delete <strong>all {nodes.length} memories</strong>? This cannot be undone.</p>
            <div className="graph-viewport__confirm-btns">
              <button className="btn-danger-sm" onClick={() => { onDeleteAll?.(); setConfirmClearAll(false); }}>Delete All</button>
              <button className="btn-ghost-sm" onClick={() => setConfirmClearAll(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}

      <div className="graph-viewport__legend">
        <span className="graph-viewport__legend-item"><span className="graph-viewport__legend-dot" style={{ background: '#5B9BD5' }} />Episodic</span>
        <span className="graph-viewport__legend-item"><span className="graph-viewport__legend-hex" />Concept</span>
        <span className="graph-viewport__legend-item"><span className="graph-viewport__legend-dot" style={{ background: '#6BAF7A' }} />Activated</span>
        <span className="graph-viewport__legend-item"><span className="graph-viewport__legend-dot" style={{ background: '#4A4A54', opacity: 0.5 }} />Pruned</span>
        <span className="graph-viewport__legend-item"><span className="graph-viewport__legend-dot" style={{ background: '#8B2525' }} />Superseded</span>
        <span className="graph-viewport__legend-mode">{is3D ? '⟳ drag · scroll zoom' : '● force layout'}</span>
      </div>
    </div>
  );
}
