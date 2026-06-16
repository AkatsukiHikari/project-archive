<template>
  <div class="relative rounded-xl overflow-hidden" style="background:#0a1020">
    <div ref="canvasWrap" style="width:100%;height:460px" />
    <!-- hover 提示 -->
    <div
      v-if="hover"
      class="absolute top-3 left-3 px-3 py-1.5 rounded-lg text-[12px] pointer-events-none"
      style="background:rgba(10,16,32,0.85);border:1px solid #2a3a66;color:#cdd9ff"
    >
      架位 {{ hover.code }} · {{ hover.used }}/{{ hover.capacity }}（{{ hover.pct }}%）
    </div>
    <!-- 操作提示 -->
    <div class="absolute bottom-3 right-3 text-[11px] pointer-events-none" style="color:#5a6c9e">
      左键拖动旋转 · 滚轮缩放 · 点击架位管理
    </div>
  </div>
</template>

<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";
import type { Shelf } from "@/api/storage";

const props = defineProps<{ shelves: Shelf[]; rows: number; columns: number; layers: number }>();
const emit = defineEmits<{ pick: [Shelf] }>();

const canvasWrap = ref<HTMLElement | null>(null);
const hover = ref<{ code: string; used: number; capacity: number; pct: number } | null>(null);

// three.js 运行时句柄（动态加载，仅客户端）
let cleanup: (() => void) | null = null;

function fillColorHex(p: number): number {
  if (p >= 90) return 0xc2483f;
  if (p >= 70) return 0xc79a3a;
  if (p > 0) return 0x2f9e73;
  return 0x33415f;
}

onMounted(async () => {
  const el = canvasWrap.value;
  if (!el) return;

  // 动态 import：three 仅在客户端加载，且独立代码分块、不进首屏包
  const THREE = await import("three");
  const { OrbitControls } = await import("three/examples/jsm/controls/OrbitControls.js");

  const width = el.clientWidth || 800;
  const height = el.clientHeight || 460;

  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x0a1020);

  const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  el.appendChild(renderer.domElement);

  // 灯光
  scene.add(new THREE.AmbientLight(0xffffff, 0.65));
  const dir = new THREE.DirectionalLight(0xffffff, 0.9);
  dir.position.set(8, 16, 10);
  scene.add(dir);
  const dir2 = new THREE.DirectionalLight(0x6688ff, 0.35);
  dir2.position.set(-10, 6, -8);
  scene.add(dir2);

  // 布局参数：列沿 X，排沿 Z（纵深），层沿 Y
  const SX = 1.5, SZ = 1.7, LAYER_H = 0.34, BOX = 1.15;
  const offX = ((props.columns - 1) * SX) / 2;
  const offZ = ((props.rows - 1) * SZ) / 2;
  const layers = Math.max(1, props.layers);

  const root = new THREE.Group();
  scene.add(root);

  // 地面
  const floorMax = Math.max(props.columns * SX, props.rows * SZ) + 2;
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(props.columns * SX + 2, props.rows * SZ + 2),
    new THREE.MeshStandardMaterial({ color: 0x12203f, roughness: 0.95, metalness: 0 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.05;
  root.add(floor);
  const grid = new THREE.GridHelper(floorMax, Math.round(floorMax), 0x24345f, 0x1a2747);
  (grid.material as { opacity: number; transparent: boolean }).opacity = 0.4;
  (grid.material as { transparent: boolean }).transparent = true;
  root.add(grid);

  // 共享几何体
  const layerGeo = new THREE.BoxGeometry(BOX, LAYER_H * 0.82, BOX);
  // 每个架位的网格集合（用于 hover 高亮）
  const shelfMeshes = new Map<string, THREE.Mesh[]>();
  const pickable: THREE.Mesh[] = [];

  for (const s of props.shelves) {
    const cap = s.capacity || 0;
    const used = s.used || 0;
    const pct = cap ? Math.round((used / cap) * 100) : 0;
    const litLayers = used > 0 ? Math.max(1, Math.min(layers, Math.round((used / cap) * layers))) : 0;
    const litColor = fillColorHex(pct);

    const x = s.col_index * SX - offX;
    const z = s.row_index * SZ - offZ;
    const meshes: THREE.Mesh[] = [];

    for (let ly = 0; ly < layers; ly++) {
      const isLit = ly < litLayers;
      const mat = new THREE.MeshStandardMaterial({
        color: isLit ? litColor : 0x1b2747,
        roughness: 0.55,
        metalness: 0.15,
        transparent: !isLit,
        opacity: isLit ? 1 : 0.5,
      });
      const m = new THREE.Mesh(layerGeo, mat);
      m.position.set(x, ly * LAYER_H + LAYER_H / 2, z);
      m.userData.shelf = s;
      m.userData.baseEmissive = isLit ? litColor : 0x000000;
      mat.emissive = new THREE.Color(isLit ? litColor : 0x000000);
      mat.emissiveIntensity = isLit ? 0.12 : 0;
      root.add(m);
      meshes.push(m);
      pickable.push(m);
    }
    shelfMeshes.set(s.id, meshes);
  }

  // 相机初始位置
  const span = Math.max(props.columns * SX, props.rows * SZ);
  camera.position.set(span * 0.7, span * 0.85 + 4, span * 1.1 + 4);
  const controls = new OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true;
  controls.dampingFactor = 0.08;
  controls.target.set(0, layers * LAYER_H * 0.4, 0);
  controls.maxPolarAngle = Math.PI / 2.05;
  controls.update();

  // 拾取
  const raycaster = new THREE.Raycaster();
  const pointer = new THREE.Vector2();
  let hoveredId: string | null = null;

  function setHighlight(id: string | null) {
    if (hoveredId === id) return;
    // 还原旧的
    if (hoveredId) {
      for (const m of shelfMeshes.get(hoveredId) ?? []) {
        const mat = m.material as { emissiveIntensity: number; emissive: { setHex: (h: number) => void } };
        mat.emissive.setHex(m.userData.baseEmissive as number);
        mat.emissiveIntensity = (m.userData.baseEmissive as number) ? 0.12 : 0;
      }
    }
    hoveredId = id;
    if (id) {
      for (const m of shelfMeshes.get(id) ?? []) {
        const mat = m.material as { emissiveIntensity: number; emissive: { setHex: (h: number) => void } };
        mat.emissive.setHex(0x4f8fff);
        mat.emissiveIntensity = 0.5;
      }
    }
  }

  function pickAt(clientX: number, clientY: number): THREE.Mesh | null {
    const rect = renderer.domElement.getBoundingClientRect();
    pointer.x = ((clientX - rect.left) / rect.width) * 2 - 1;
    pointer.y = -((clientY - rect.top) / rect.height) * 2 + 1;
    raycaster.setFromCamera(pointer, camera);
    const hits = raycaster.intersectObjects(pickable, false);
    return hits.length ? (hits[0].object as THREE.Mesh) : null;
  }

  function onMove(e: PointerEvent) {
    const m = pickAt(e.clientX, e.clientY);
    const s = m?.userData.shelf as Shelf | undefined;
    if (s) {
      setHighlight(s.id);
      const cap = s.capacity || 0;
      hover.value = { code: s.code, used: s.used || 0, capacity: cap, pct: cap ? Math.round((s.used / cap) * 100) : 0 };
      renderer.domElement.style.cursor = "pointer";
    } else {
      setHighlight(null);
      hover.value = null;
      renderer.domElement.style.cursor = "grab";
    }
  }

  let downX = 0, downY = 0;
  function onDown(e: PointerEvent) { downX = e.clientX; downY = e.clientY; }
  function onUp(e: PointerEvent) {
    // 区分拖动与点击
    if (Math.abs(e.clientX - downX) > 4 || Math.abs(e.clientY - downY) > 4) return;
    const m = pickAt(e.clientX, e.clientY);
    const s = m?.userData.shelf as Shelf | undefined;
    if (s) emit("pick", s);
  }

  renderer.domElement.addEventListener("pointermove", onMove);
  renderer.domElement.addEventListener("pointerdown", onDown);
  renderer.domElement.addEventListener("pointerup", onUp);

  // 渲染循环
  let raf = 0;
  const tick = () => {
    controls.update();
    renderer.render(scene, camera);
    raf = requestAnimationFrame(tick);
  };
  tick();

  // 自适应
  const ro = new ResizeObserver(() => {
    const w = el.clientWidth, hgt = el.clientHeight;
    if (w && hgt) {
      camera.aspect = w / hgt;
      camera.updateProjectionMatrix();
      renderer.setSize(w, hgt);
    }
  });
  ro.observe(el);

  // 清理
  cleanup = () => {
    cancelAnimationFrame(raf);
    ro.disconnect();
    renderer.domElement.removeEventListener("pointermove", onMove);
    renderer.domElement.removeEventListener("pointerdown", onDown);
    renderer.domElement.removeEventListener("pointerup", onUp);
    controls.dispose();
    layerGeo.dispose();
    floor.geometry.dispose();
    (floor.material as { dispose: () => void }).dispose();
    pickable.forEach((m) => (m.material as { dispose: () => void }).dispose());
    renderer.dispose();
    if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
  };
});

onBeforeUnmount(() => { cleanup?.(); });
</script>
