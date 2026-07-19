<template>
  <div class="min-h-screen flex flex-col" style="background: var(--semi-color-bg-1)">
    <!-- ── 顶部 ─────────────────────────────────────────── -->
    <header
      class="h-20 flex items-center px-8 gap-4 shrink-0"
      style="background: var(--semi-color-bg-0); border-bottom: 1px solid var(--semi-color-border)"
    >
      <LogoIcon :size="40" />
      <div>
        <div class="text-[20px] font-bold leading-tight" style="color: var(--semi-color-text-0)">档案自助查询</div>
        <div class="text-[12px]" style="color: var(--semi-color-text-3)">仅可检索开放档案 · 查看原文需工作人员批准</div>
      </div>
      <div class="flex-1" />
      <NButton size="large" tertiary @click="retrieveShow = true">
        <template #icon><Icon name="heroicons:ticket" class="w-5 h-5" /></template>
        凭申请码查进度
      </NButton>
      <NButton v-if="cart.length" size="large" type="primary" @click="cartShow = true">
        <template #icon><Icon name="heroicons:shopping-bag" class="w-5 h-5" /></template>
        申请篮（{{ cart.length }}）
      </NButton>
    </header>

    <!-- ── 检索区 ───────────────────────────────────────── -->
    <div class="px-8 pt-6 pb-4 shrink-0">
      <div class="flex items-stretch gap-3 max-w-4xl mx-auto">
        <NInput
          v-model:value="keyword"
          size="large"
          clearable
          placeholder="输入 题名 / 姓名 / 档号 关键词，如「结婚登记」「李明」"
          class="flex-1 text-[16px]"
          @keydown.enter="search"
        >
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-5 h-5" style="color: var(--semi-color-text-3)" /></template>
        </NInput>
        <NInputNumber v-model:value="year" size="large" :show-button="false" placeholder="年度（选填）" style="width: 140px" />
        <NButton size="large" type="primary" :loading="loading" style="min-width: 110px" @click="search">检 索</NButton>
      </div>
    </div>

    <!-- ── 结果区 ───────────────────────────────────────── -->
    <main class="flex-1 min-h-0 overflow-y-auto px-8 pb-8">
      <div class="max-w-4xl mx-auto flex flex-col gap-2.5">
        <div v-if="!searched" class="flex flex-col items-center gap-3 py-20" style="color: var(--semi-color-text-3)">
          <Icon name="heroicons:magnifying-glass-circle" class="w-14 h-14" />
          <span class="text-[15px]">输入关键词开始检索，选中档案后提交查看申请</span>
        </div>
        <div v-else-if="rows.length === 0 && !loading" class="flex flex-col items-center gap-3 py-20" style="color: var(--semi-color-text-3)">
          <Icon name="heroicons:inbox" class="w-14 h-14" />
          <span class="text-[15px]">未检索到相关开放档案，可调整关键词重试或到柜台咨询</span>
        </div>

        <template v-else>
          <div class="text-[13px]" style="color: var(--semi-color-text-2)">共检索到 <strong>{{ total }}</strong> 件开放档案</div>
          <div
            v-for="r in rows"
            :key="r.id"
            class="pro-card px-5 py-4 flex items-center gap-4"
          >
            <div class="flex-1 min-w-0">
              <div class="text-[16px] font-medium truncate" style="color: var(--semi-color-text-0)">{{ r.TM }}</div>
              <div class="text-[13px] mt-1 flex items-center gap-3" style="color: var(--semi-color-text-3)">
                <span class="font-mono">{{ r.DH || "—" }}</span>
                <span v-if="r.ND">{{ r.ND }} 年</span>
                <span v-if="r.RZZ">{{ r.RZZ }}</span>
              </div>
            </div>
            <NButton
              v-if="!inCart(r.id)"
              size="large"
              type="primary"
              secondary
              @click="addToCart(r)"
            >
              <template #icon><Icon name="heroicons:plus" class="w-5 h-5" /></template>
              加入申请
            </NButton>
            <NButton v-else size="large" tertiary @click="removeFromCart(r.id)">
              <template #icon><Icon name="heroicons:check" class="w-5 h-5" /></template>
              已加入
            </NButton>
          </div>
          <div class="flex justify-center pt-2">
            <NPagination v-model:page="page" :page-count="pageCount" size="large" @update:page="load" />
          </div>
        </template>
      </div>
    </main>

    <!-- ── 申请篮 + 提交 ─────────────────────────────────── -->
    <NModal v-model:show="cartShow" preset="card" title="提交查看申请" style="width: 640px">
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1.5 max-h-[240px] overflow-y-auto">
          <div
            v-for="(it, i) in cart"
            :key="it.id"
            class="flex items-center gap-3 rounded-lg border px-3 py-2"
            style="border-color: var(--semi-color-border)"
          >
            <span class="text-[13px] tabular-nums" style="color: var(--semi-color-text-3)">{{ i + 1 }}</span>
            <div class="flex-1 min-w-0">
              <div class="text-[14px] truncate" style="color: var(--semi-color-text-0)">{{ it.TM }}</div>
              <div class="text-[12px] font-mono" style="color: var(--semi-color-text-3)">{{ it.DH || "—" }}</div>
            </div>
            <NButton size="small" tertiary type="error" @click="removeFromCart(it.id)">移除</NButton>
          </div>
        </div>

        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1">
            <span class="text-[13px]" style="color: var(--semi-color-text-2)">姓名 <span style="color: var(--semi-color-danger)">*</span></span>
            <NInput v-model:value="form.applicant_name" size="large" placeholder="请输入您的姓名" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[13px]" style="color: var(--semi-color-text-2)">联系电话 <span style="color: var(--semi-color-danger)">*</span></span>
            <NInput v-model:value="form.phone" size="large" placeholder="用于工作人员联系您" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[13px]" style="color: var(--semi-color-text-2)">身份证号（选填）</span>
            <NInput v-model:value="form.id_card_no" size="large" placeholder="涉个人档案建议填写以便核验" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-[13px]" style="color: var(--semi-color-text-2)">查档用途（选填）</span>
            <NInput v-model:value="form.purpose" size="large" placeholder="如：办理房产继承" />
          </div>
        </div>

        <NButton size="large" type="primary" block :loading="submitting" @click="submitApply">
          提交申请（{{ cart.length }} 件）
        </NButton>
      </div>
    </NModal>

    <!-- ── 申请码展示 ───────────────────────────────────── -->
    <NModal v-model:show="codeShow" preset="card" title="申请已提交" style="width: 520px" :mask-closable="false">
      <div class="flex flex-col items-center gap-4 py-4">
        <Icon name="heroicons:check-circle" class="w-14 h-14" style="color: var(--semi-color-success)" />
        <div class="text-[15px]" style="color: var(--semi-color-text-1)">请记住您的申请码</div>
        <div
          class="text-[44px] font-bold tracking-[0.3em] font-mono px-8 py-3 rounded-xl"
          style="color: oklch(var(--p)); background: color-mix(in srgb, oklch(var(--p)) 8%, transparent)"
        >{{ submitResult?.access_code }}</div>
        <div class="text-[13px] text-center leading-relaxed" style="color: var(--semi-color-text-2)">
          登记号 {{ submitResult?.reg_no }}。工作人员批准后，<br >
          您可在本机或任意自助机点击「凭申请码查进度」查看档案原文。
        </div>
        <NButton size="large" type="primary" @click="closeCodeModal">我已记住，完成</NButton>
      </div>
    </NModal>

    <!-- ── 进度 / 阅览 ──────────────────────────────────── -->
    <NModal v-model:show="retrieveShow" preset="card" title="查询申请进度" style="width: 640px">
      <div class="flex flex-col gap-4">
        <div class="flex items-stretch gap-3">
          <NInput
            v-model:value="retrieveCode"
            size="large"
            maxlength="6"
            placeholder="请输入 6 位申请码"
            class="flex-1 font-mono text-[18px] tracking-widest"
            @keydown.enter="checkStatus"
          />
          <NButton size="large" type="primary" :loading="checking" @click="checkStatus">查 询</NButton>
        </div>

        <template v-if="statusResult">
          <div v-if="!statusResult.ok" class="text-[14px] py-4 text-center" style="color: var(--semi-color-danger)">
            {{ statusResult.reason }}
          </div>
          <template v-else>
            <div class="flex items-center gap-3 rounded-lg px-4 py-3" :style="statusBanner.style">
              <Icon :name="statusBanner.icon" class="w-6 h-6 shrink-0" />
              <div class="flex flex-col">
                <span class="text-[14px] font-medium">{{ statusBanner.title }}</span>
                <span class="text-[12.5px] opacity-80">{{ statusBanner.desc }}</span>
              </div>
            </div>
            <div class="flex flex-col gap-1.5 max-h-[260px] overflow-y-auto">
              <div
                v-for="it in statusResult.items"
                :key="it.archive_id"
                class="flex items-center gap-3 rounded-lg border px-3 py-2.5"
                style="border-color: var(--semi-color-border)"
              >
                <div class="flex-1 min-w-0">
                  <div class="text-[14px] truncate" style="color: var(--semi-color-text-0)">{{ it.TM }}</div>
                  <div class="text-[12px] font-mono" style="color: var(--semi-color-text-3)">{{ it.DH || "—" }}</div>
                </div>
                <NButton
                  size="large"
                  type="primary"
                  secondary
                  :disabled="!statusResult.viewable"
                  :loading="openingId === it.archive_id"
                  @click="openViewer(it)"
                >
                  {{ statusResult.viewable ? "查看原文" : "待批准" }}
                </NButton>
              </div>
            </div>
          </template>
        </template>
      </div>
    </NModal>

    <!-- ── 原文阅览（全屏覆盖，无下载/打印入口） ─────────── -->
    <div v-if="viewerShow" class="fixed inset-0 z-[100] flex flex-col" style="background: rgba(0,0,0,0.92)">
      <div class="h-16 flex items-center px-6 gap-3 shrink-0">
        <span class="text-[15px] font-medium text-white/90 truncate">{{ viewerTitle }}</span>
        <span class="text-[12px] text-white/50">仅限馆内阅览</span>
        <div class="flex-1" />
        <NButton size="large" type="primary" @click="viewerShow = false">
          <template #icon><Icon name="heroicons:x-mark" class="w-5 h-5" /></template>
          关闭阅览
        </NButton>
      </div>
      <iframe v-if="viewerUrl" :src="viewerUrl" class="flex-1 w-full border-none" title="档案原文" />
      <div v-else class="flex-1 flex items-center justify-center text-white/70 text-[15px]">原文加载中…</div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { NButton, NInput, NInputNumber, NModal, NPagination, useMessage } from "naive-ui";
import LogoIcon from "@/components/common/LogoIcon.vue";
import { ArchiveAPI, type Archive } from "@/api/repository";
import { UtilizationAPI, type KioskStatusResult } from "@/api/utilization";

// 自助机专用全屏页：无后台外壳/页签；设备账号登录后由民众自助操作
definePageMeta({ layout: false, middleware: "auth" });
useHead({ title: "档案自助查询" });

const message = useMessage();

const CODE_KEY = "sams_kiosk_code";

// ── 检索（仅开放档案：正式库 + 无密级） ───────────────────────────────────────
const keyword = ref("");
const year = ref<number | null>(null);
const rows = ref<Archive[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = 10;
const loading = ref(false);
const searched = ref(false);
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize)));

async function load() {
  loading.value = true;
  try {
    const res = await ArchiveAPI.list({
      source: "formal",
      MJ: "无",
      keyword: keyword.value.trim() || undefined,
      ND_from: year.value ?? undefined,
      ND_to: year.value ?? undefined,
      page: page.value,
      page_size: pageSize,
    });
    rows.value = res.data.items;
    total.value = res.data.total;
    searched.value = true;
  } finally {
    loading.value = false;
  }
}
function search() {
  if (!keyword.value.trim() && !year.value) {
    message.warning("请输入检索关键词");
    return;
  }
  page.value = 1;
  load();
}

// ── 申请篮 ────────────────────────────────────────────────────────────────────
const cart = ref<Archive[]>([]);
const cartShow = ref(false);
const inCart = (id: string) => cart.value.some((c) => c.id === id);
function addToCart(r: Archive) {
  if (!inCart(r.id)) cart.value = [...cart.value, r];
}
function removeFromCart(id: string) {
  cart.value = cart.value.filter((c) => c.id !== id);
  if (cart.value.length === 0) cartShow.value = false;
}

// ── 提交申请 ──────────────────────────────────────────────────────────────────
const form = reactive({ applicant_name: "", phone: "", id_card_no: "", purpose: "" });
const submitting = ref(false);
const submitResult = ref<{ reg_no: string; access_code: string } | null>(null);
const codeShow = ref(false);

async function submitApply() {
  if (!form.applicant_name.trim()) return message.warning("请填写姓名");
  if (!form.phone.trim()) return message.warning("请填写联系电话");
  submitting.value = true;
  try {
    const res = await UtilizationAPI.kioskApply({
      applicant_name: form.applicant_name.trim(),
      phone: form.phone.trim(),
      id_card_no: form.id_card_no.trim() || undefined,
      purpose: form.purpose.trim() || undefined,
      items: cart.value.map((r) => ({
        archive_id: r.id, DH: r.DH ?? null, TM: r.TM, RZZ: r.RZZ ?? null, ND: r.ND ?? null, QZH: r.QZH ?? null,
      })),
    });
    if (res.code !== 0) return message.error(res.message);
    submitResult.value = res.data;
    localStorage.setItem(CODE_KEY, res.data.access_code);
    cart.value = [];
    cartShow.value = false;
    Object.assign(form, { applicant_name: "", phone: "", id_card_no: "", purpose: "" });
    codeShow.value = true;
  } finally {
    submitting.value = false;
  }
}
function closeCodeModal() {
  codeShow.value = false;
  retrieveCode.value = submitResult.value?.access_code ?? "";
}

// ── 进度查询 / 阅览 ───────────────────────────────────────────────────────────
const retrieveShow = ref(false);
const retrieveCode = ref(localStorage.getItem(CODE_KEY) ?? "");
const checking = ref(false);
const statusResult = ref<KioskStatusResult | null>(null);

async function checkStatus() {
  const code = retrieveCode.value.trim();
  if (code.length < 4) return message.warning("请输入完整申请码");
  checking.value = true;
  try {
    const res = await UtilizationAPI.kioskStatus(code);
    if (res.code !== 0) return message.error(res.message);
    statusResult.value = res.data;
  } finally {
    checking.value = false;
  }
}

const statusBanner = computed(() => {
  const s = statusResult.value?.status;
  if (s === "pending") {
    return {
      icon: "heroicons:clock",
      title: "等待工作人员审批",
      desc: "请稍候，批准后即可在本机查看原文；如需加急请到柜台联系工作人员",
      style: "background: color-mix(in srgb, var(--semi-color-warning) 10%, transparent); color: var(--semi-color-warning)",
    };
  }
  if (s === "processing") {
    return {
      icon: "heroicons:check-circle",
      title: "已批准，可以查看",
      desc: "点击下方「查看原文」在本机阅览（仅限馆内，不提供下载打印）",
      style: "background: color-mix(in srgb, var(--semi-color-success) 10%, transparent); color: var(--semi-color-success)",
    };
  }
  if (s === "rejected") {
    return {
      icon: "heroicons:x-circle",
      title: "申请未通过",
      desc: statusResult.value?.reject_reason || "如有疑问请到柜台咨询工作人员",
      style: "background: color-mix(in srgb, var(--semi-color-danger) 10%, transparent); color: var(--semi-color-danger)",
    };
  }
  return {
    icon: "heroicons:archive-box",
    title: "本次办理已结束",
    desc: "申请码已失效，如需再次查看请重新提交申请",
    style: "background: var(--semi-color-fill-0); color: var(--semi-color-text-2)",
  };
});

const viewerShow = ref(false);
const viewerUrl = ref("");
const viewerTitle = ref("");
const openingId = ref<string | null>(null);

async function openViewer(it: { archive_id: string; TM: string }) {
  openingId.value = it.archive_id;
  try {
    const res = await UtilizationAPI.kioskAttachments(retrieveCode.value.trim(), it.archive_id);
    if (res.code !== 0) return message.error(res.message);
    const target = res.data.find((a) => a.url);
    if (!target?.url) return message.warning("该档案原文暂无法读取，请联系工作人员");
    // #toolbar=0 隐藏浏览器 PDF 工具栏（下载/打印按钮），配合自助机全屏模式使用
    viewerUrl.value = `${target.url}#toolbar=0&navpanes=0`;
    viewerTitle.value = it.TM;
    viewerShow.value = true;
  } finally {
    openingId.value = null;
  }
}
</script>
