<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader title="证明开具" description="依据所利用档案开具档案利用证明，自动编号、可打印" icon="heroicons:identification" />

    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect v-model:value="bizFilter" :options="bizOptions" placeholder="全部状态" clearable style="width: 140px" @update:value="load" />
      <NInput v-model:value="keyword" placeholder="申请人 / 登记号 / 证明编号" clearable style="width: 220px" @keydown.enter="load">
        <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
      </NInput>
      <NButton tertiary @click="load">刷新</NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="showRegister = true">
        <template #icon><Icon name="heroicons:identification" class="w-4 h-4" /></template>
        登记证明申请
      </NButton>
    </div>

    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="filteredRows" :loading="loading" :page-size="15" size="small" />
    </div>

    <RegisterApplicantModal v-model:show="showRegister" use-type="certificate" @created="onRegistered" />

    <NDrawer v-model:show="showDetail" :width="480" placement="right">
      <NDrawerContent :title="`证明登记 · ${detailReg}`" closable>
        <ApplicationDetailPanel :app-id="detailId" :show-actions="false" />
      </NDrawerContent>
    </NDrawer>

    <NModal v-model:show="showIssue" preset="card" title="开具档案利用证明" style="width: 600px; max-width: 95vw">
      <div class="flex flex-col gap-2">
        <span class="text-sm" style="color:var(--semi-color-text-2)">证明事项 / 内容</span>
        <NInput v-model:value="certContent" type="textarea" :rows="6" placeholder="如：兹证明 XXX 因工作查考利用本馆相关档案，内容属实……" />
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton @click="showIssue = false">取消</NButton>
          <NButton type="primary" :loading="acting" @click="confirmIssue">开具并编号</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, h } from "vue";
import { useRouter } from "vue-router";
import { NSelect, NInput, NButton, NTag, NModal, NDrawer, NDrawerContent, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { RegisterApplicantModal, ApplicationDetailPanel } from "@/components/archive";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplication } from "@/api/utilization";

definePageMeta({
  layout: "service",
  middleware: "auth",
  breadcrumb: [
    { name: "利用服务中心", path: "/service" },
    { name: "证明开具", path: "/service/certificate" },
  ],
});

const router = useRouter();
const message = useMessage();

const bizOptions = [{ label: "待开具", value: "待开具" }, { label: "已出具", value: "已出具" }];
const BIZ_TONE: Record<string, "default" | "success"> = { 待开具: "default", 已出具: "success" };

const loading = ref(false);
const rows = ref<UtilApplication[]>([]);
const bizFilter = ref<string | null>(null);
const keyword = ref("");
const filteredRows = computed(() => bizFilter.value ? rows.value.filter((r) => r.biz_status === bizFilter.value) : rows.value);

async function load() {
  loading.value = true;
  try {
    rows.value = (await UtilizationAPI.list({ use_type: "certificate", keyword: keyword.value.trim() || undefined })).data;
  } finally {
    loading.value = false;
  }
}

const fmt = (s?: string | null) => (s ? s.slice(0, 10) : "—");

const columns: DataTableColumns<UtilApplication> = [
  { title: "登记号", key: "reg_no", width: 150, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.reg_no) },
  { title: "申请人", key: "applicant_name", width: 90 },
  { title: "工作单位", key: "organization", minWidth: 120, render: (r) => r.organization || "—" },
  { title: "调阅篮", key: "item_count", width: 70, render: (r) => `${r.item_count} 件` },
  { title: "状态", key: "biz_status", width: 90, render: (r) => h(NTag, { size: "small", type: BIZ_TONE[r.biz_status ?? ""] ?? "default" }, () => r.biz_status ?? "—") },
  { title: "证明编号", key: "cert_no", width: 160, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.cert_no || "—") },
  { title: "出具日期", key: "issued_at", width: 110, render: (r) => fmt(r.issued_at) },
  {
    title: "操作", key: "actions", width: 200, fixed: "right",
    render: (r) => {
      const btns = [];
      if (r.biz_status === "待开具") {
        btns.push(h(NButton, { size: "small", tertiary: true, onClick: () => goProcess(r) }, () => "选档"));
        btns.push(h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openIssue(r) }, () => "开具"));
      } else {
        btns.push(h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => printCert(r) }, () => "打印"));
      }
      btns.push(h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r) }, () => "详情"));
      return h("div", { class: "flex gap-2" }, btns);
    },
  },
];

const showRegister = ref(false);
function onRegistered(app: UtilApplication) { router.push(`/service/reading?app=${app.id}`); }
function goProcess(r: UtilApplication) { router.push(`/service/reading?app=${r.id}`); }

// ── 开具 ──────────────────────────────────────────────────────────
const showIssue = ref(false);
const issueTarget = ref<UtilApplication | null>(null);
const certContent = ref("");
const acting = ref(false);

function openIssue(r: UtilApplication) {
  issueTarget.value = r;
  certContent.value = `兹证明 ${r.applicant_name} 因${r.purpose || "工作需要"}利用本馆相关档案，所涉档案内容属实。特此证明。`;
  showIssue.value = true;
}
async function confirmIssue() {
  if (!issueTarget.value || !certContent.value.trim()) { message.warning("请填写证明内容"); return; }
  acting.value = true;
  try {
    await UtilizationAPI.issueCert(issueTarget.value.id, certContent.value.trim());
    message.success("已开具证明");
    showIssue.value = false;
    await load();
  } finally {
    acting.value = false;
  }
}

// ── 打印证明 ──────────────────────────────────────────────────────
async function printCert(r: UtilApplication) {
  const detail = (await UtilizationAPI.get(r.id)).data;
  const w = window.open("", "_blank");
  if (!w) { message.warning("打印窗口被拦截，请允许弹窗"); return; }
  const esc = (v: string) => v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const items = detail.items.map((it, i) => `<tr><td>${i + 1}</td><td>${esc(it.DH || "—")}</td><td>${esc(it.TM)}</td><td>${it.ND ?? "—"}</td></tr>`).join("");
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>档案利用证明</title>
    <style>
      body{font-family:"SimSun","Microsoft YaHei",serif;padding:60px 72px;color:#000;line-height:2}
      h1{text-align:center;font-size:26px;letter-spacing:6px;margin-bottom:8px}
      .no{text-align:center;color:#444;font-size:13px;margin-bottom:36px}
      .body{font-size:16px;text-indent:2em;margin-bottom:16px}
      table{width:100%;border-collapse:collapse;font-size:13px;margin:12px 0}
      th,td{border:1px solid #333;padding:5px 8px;text-align:left}
      .sign{margin-top:60px;text-align:right;font-size:15px;line-height:2.2}
    </style></head><body>
    <h1>档案利用证明</h1>
    <div class="no">编号：${esc(detail.cert_no || "")}</div>
    <p class="body">${esc(detail.cert_content || "")}</p>
    <p class="body">所利用档案如下（共 ${detail.items.length} 件）：</p>
    <table><thead><tr><th>序号</th><th>档号</th><th>题名</th><th>年度</th></tr></thead><tbody>${items}</tbody></table>
    <div class="sign">
      经办人：${esc(detail.handler_name || "&nbsp;&nbsp;")}<br/>
      档案馆（盖章）：&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;<br/>
      ${new Date(detail.issued_at || Date.now()).toLocaleDateString("zh-CN")}
    </div>
    </body></html>`);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 300);
}

// ── 详情 ──────────────────────────────────────────────────────────
const showDetail = ref(false);
const detailId = ref<string | null>(null);
const detailReg = ref("");
function openDetail(r: UtilApplication) { detailId.value = r.id; detailReg.value = r.reg_no; showDetail.value = true; }

onMounted(load);
</script>
