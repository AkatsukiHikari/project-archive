<template>
  <div class="relative rounded-xl overflow-hidden" style="background:#1c2742">
    <div ref="canvasWrap" style="width:100%;height:460px" />
    <!-- hover 提示 -->
    <div
      v-if="hover"
      class="absolute top-3 left-3 px-3 py-1.5 rounded-lg text-[12px] pointer-events-none"
      style="background:rgba(255,255,255,0.92);border:1px solid #c2ccde;color:#2a3550;box-shadow:0 2px 8px rgba(40,60,110,0.12)"
    >
      架位 {{ hover.code }} · {{ hover.used }}/{{ hover.capacity }}（{{ hover.pct }}%）
    </div>
    <!-- 颜色图例 -->
    <div
      class="absolute top-3 right-3 px-3 py-2.5 rounded-lg text-[11.5px] pointer-events-none flex flex-col gap-1.5"
      style="background:rgba(255,255,255,0.92);border:1px solid #c2ccde;color:#4a5670;box-shadow:0 2px 8px rgba(40,60,110,0.12)"
    >
      <span class="font-semibold" style="color:#2a3550">架位占用率</span>
      <span class="flex items-center gap-1.5"><i class="w-3 h-3 rounded-sm inline-block" style="background:#37c98c" />0–70% 充足</span>
      <span class="flex items-center gap-1.5"><i class="w-3 h-3 rounded-sm inline-block" style="background:#eaad42" />70–90% 较满</span>
      <span class="flex items-center gap-1.5"><i class="w-3 h-3 rounded-sm inline-block" style="background:#e85d4e" />≥90% 接近饱和</span>
      <span class="flex items-center gap-1.5"><i class="w-3 h-3 rounded-sm inline-block" style="background:#d3d7de;border:1px solid #b9c0cc" />空置 / 未上架</span>
    </div>
    <!-- 操作提示 -->
    <div class="absolute bottom-3 right-3 text-[11px] pointer-events-none" style="color:#8fa0c4">
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
  if (p >= 90) return 0xe85d4e;
  if (p >= 70) return 0xeaad42;
  if (p > 0) return 0x37c98c;
  return 0x33415f;
}

onMounted(async () => {
  const el = canvasWrap.value;
  if (!el) return;

  // 动态 import：three 仅在客户端加载，且独立代码分块、不进首屏包
  const THREE = await import("three");
  const { OrbitControls } = await import("three/examples/jsm/controls/OrbitControls.js");
  const { RoomEnvironment } = await import("three/examples/jsm/environments/RoomEnvironment.js");

  const width = el.clientWidth || 800;
  const height = el.clientHeight || 460;

  const scene = new THREE.Scene();
  // 纵向渐变背景，比纯色更有空间感
  const bgCanvas = document.createElement("canvas");
  bgCanvas.width = 2; bgCanvas.height = 256;
  const bgCtx = bgCanvas.getContext("2d")!;
  const bgGrad = bgCtx.createLinearGradient(0, 0, 0, 256);
  bgGrad.addColorStop(0, "#33405f");
  bgGrad.addColorStop(0.5, "#222d49");
  bgGrad.addColorStop(1, "#161f38");
  bgCtx.fillStyle = bgGrad;
  bgCtx.fillRect(0, 0, 2, 256);
  const bgTex = new THREE.CanvasTexture(bgCanvas);
  bgTex.colorSpace = THREE.SRGBColorSpace;
  scene.background = bgTex;

  const camera = new THREE.PerspectiveCamera(50, width / height, 0.1, 1000);
  const renderer = new THREE.WebGLRenderer({ antialias: true });
  renderer.setSize(width, height);
  renderer.setPixelRatio(Math.min(window.devicePixelRatio, 2));
  renderer.shadowMap.enabled = true;
  renderer.shadowMap.type = THREE.PCFSoftShadowMap;
  renderer.toneMapping = THREE.ACESFilmicToneMapping;
  renderer.toneMappingExposure = 1.0;
  renderer.outputColorSpace = THREE.SRGBColorSpace;
  el.appendChild(renderer.domElement);

  // 环境贴图：金属表面必须有可反射的环境，否则银色金属会渲染成黑色
  const pmrem = new THREE.PMREMGenerator(renderer);
  const envTex = pmrem.fromScene(new RoomEnvironment(), 0.04).texture;
  scene.environment = envTex;

  // 深色纵深雾，远处柜体自然没入背景，增强空间纵深
  scene.fog = new THREE.Fog(0x1c2742, 36, 88);

  // 灯光：环境贴图已提供柔和漫反射，这里只补一盏主光投阴影 + 轻补光
  scene.add(new THREE.AmbientLight(0xffffff, 0.25));
  const dir = new THREE.DirectionalLight(0xffffff, 1.0);
  dir.position.set(10, 22, 12);
  dir.castShadow = true;
  dir.shadow.mapSize.set(2048, 2048);
  dir.shadow.camera.near = 1;
  dir.shadow.camera.far = 80;
  dir.shadow.camera.left = -24;
  dir.shadow.camera.right = 24;
  dir.shadow.camera.top = 24;
  dir.shadow.camera.bottom = -24;
  dir.shadow.bias = -0.0006;
  dir.shadow.radius = 4;
  scene.add(dir);
  const fill = new THREE.DirectionalLight(0xeaf0ff, 0.35);
  fill.position.set(-12, 10, -10);
  scene.add(fill);

  // 布局参数：列沿 X，排沿 Z（纵深），层沿 Y
  const SX = 1.5, SZ = 1.7, LAYER_H = 0.34;
  const offX = ((props.columns - 1) * SX) / 2;
  const offZ = ((props.rows - 1) * SZ) / 2;
  const layers = Math.max(1, props.layers);

  const root = new THREE.Group();
  scene.add(root);

  // 地面
  const floorMax = Math.max(props.columns * SX, props.rows * SZ) + 2;
  const floor = new THREE.Mesh(
    new THREE.PlaneGeometry(floorMax + 6, floorMax + 6),
    new THREE.MeshStandardMaterial({ color: 0x2a3553, roughness: 0.45, metalness: 0.3 }),
  );
  floor.rotation.x = -Math.PI / 2;
  floor.position.y = -0.05;
  floor.receiveShadow = true;
  root.add(floor);
  const grid = new THREE.GridHelper(floorMax + 6, Math.round(floorMax + 6), 0x52639a, 0x39496e);
  grid.position.y = -0.04;
  (grid.material as { opacity: number; transparent: boolean }).opacity = 0.4;
  (grid.material as { transparent: boolean }).transparent = true;
  root.add(grid);

  // 柜体尺寸：立式档案钢柜
  const CAB_W = 1.2, CAB_D = 0.92;
  const rackH = layers * LAYER_H + 0.16;
  const frontZ = CAB_D / 2;

  // 共享几何体
  const bodyGeo = new THREE.BoxGeometry(CAB_W, rackH, CAB_D);
  const dividerGeo = new THREE.BoxGeometry(CAB_W * 0.98, 0.025, 0.02);
  const labelGeo = new THREE.BoxGeometry(CAB_W * 0.5, 0.13, 0.015);
  // 共享材质（明亮拉丝钢，靠环境贴图反射，在深色背景上鲜明）
  const cabinetMat = new THREE.MeshStandardMaterial({ color: 0xe3e7ee, roughness: 0.38, metalness: 0.7 });
  const dividerMat = new THREE.MeshStandardMaterial({ color: 0x6c7a92, roughness: 0.55, metalness: 0.55 });
  const labelMat = new THREE.MeshStandardMaterial({ color: 0xf4f6fa, roughness: 0.75, metalness: 0.05 });

  // 每个架位的柜体网格（用于 hover 高亮）
  const shelfMeshes = new Map<string, THREE.Mesh[]>();
  const pickable: THREE.Mesh[] = [];

  for (const s of props.shelves) {
    const cap = s.capacity || 0;
    const used = s.used || 0;
    const pct = cap ? Math.round((used / cap) * 100) : 0;

    const x = s.col_index * SX - offX;
    const z = s.row_index * SZ - offZ;
    const meshes: THREE.Mesh[] = [];

    // 柜体
    const body = new THREE.Mesh(bodyGeo, cabinetMat);
    body.position.set(x, rackH / 2, z);
    body.castShadow = true;
    body.receiveShadow = true;
    body.userData.shelf = s;
    body.userData.baseEmissive = 0x000000;
    body.userData.baseIntensity = 0;
    root.add(body);
    meshes.push(body);
    pickable.push(body);

    // 层分隔条（正面，呈现"分层抽屉"结构）
    for (let ly = 1; ly < layers; ly++) {
      const d = new THREE.Mesh(dividerGeo, dividerMat);
      d.position.set(x, ly * LAYER_H + 0.08, z + frontZ + 0.005);
      root.add(d);
    }

    // 顶部标签条
    const label = new THREE.Mesh(labelGeo, labelMat);
    label.position.set(x, rackH - 0.12, z + frontZ + 0.008);
    root.add(label);

    // 占用填充条：正面从下往上，高度=占用率，颜色=占用等级；空柜不显示
    if (used > 0 && cap > 0) {
      const fillH = Math.max(LAYER_H * 0.5, (used / cap) * (rackH - 0.2));
      const color = fillColorHex(pct);
      const fillMat = new THREE.MeshStandardMaterial({
        color, roughness: 0.5, metalness: 0.1,
        emissive: new THREE.Color(color), emissiveIntensity: 0.22,
      });
      const fillGeo = new THREE.BoxGeometry(CAB_W * 0.82, fillH, 0.05);
      const fill = new THREE.Mesh(fillGeo, fillMat);
      fill.position.set(x, fillH / 2 + 0.08, z + frontZ + 0.03);
      fill.castShadow = true;
      fill.userData.shelf = s;
      fill.userData.baseEmissive = color;
      fill.userData.baseIntensity = 0.22;
      fill.userData.ownGeo = fillGeo;
      root.add(fill);
      meshes.push(fill);
      pickable.push(fill);
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
        mat.emissiveIntensity = m.userData.baseIntensity as number;
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
    bodyGeo.dispose();
    dividerGeo.dispose();
    labelGeo.dispose();
    cabinetMat.dispose();
    dividerMat.dispose();
    labelMat.dispose();
    bgTex.dispose();
    envTex.dispose();
    pmrem.dispose();
    floor.geometry.dispose();
    (floor.material as { dispose: () => void }).dispose();
    // 填充条是每柜独立的几何体/材质
    pickable.forEach((m) => {
      const own = m.userData.ownGeo as { dispose: () => void } | undefined;
      if (own) {
        own.dispose();
        (m.material as { dispose: () => void }).dispose();
      }
    });
    renderer.dispose();
    if (renderer.domElement.parentNode) renderer.domElement.parentNode.removeChild(renderer.domElement);
  };
});

onBeforeUnmount(() => { cleanup?.(); });
</script>
