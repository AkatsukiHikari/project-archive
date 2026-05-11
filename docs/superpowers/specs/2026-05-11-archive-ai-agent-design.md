# 档案 AI Agent 系统设计

**日期**：2026-05-11
**作者**：架构对齐讨论结果（Hikari × Claude）
**状态**：设计稿，待评审
**目标读者**：本项目研发同事 / 客户技术对接 / 你自己将来回看

---

## 0. 摘要（一页读完）

本系统在现有 SAMS 档案平台上叠加一层"会做事的 AI Agent"能力，依托已独立部署的 Dify，
覆盖**问答 / 检索 / 摘要 / 自动挂接 / 自动编目 / 四性建议 / 拟稿 / 关联**等 9 项档案业务，
按"地基期 → 读能力期 → 写能力期 → 建议态期"四期交付。

整体采用 **γ 架构**：Dify 承担会话、模型路由、轻量 LLM 任务；后端 `app/modules/ai/`
作为 AI Gateway，集中接管身份注入、检索代理、Tool 回调、Patch 写入、审计、Eval。
所有 AI 写操作**必须**经 `ai_patch` 模块的 staging + HITL 审核队列，不允许直接写库。

风险红线：高风险能力（四性检测 / 拟稿 / 关联分析）永远以"建议形态"出现，不自动落库；
所有 AI 输出强制带可点引用，无证据则拒答；上线必须先过 Eval 黄金集准确率门禁。

---

## 1. 目标与范围

### 1.1 目标

- 让档案管理员/利用者通过自然语言对话完成 80% 以上的常规档案业务
- 不绕过任何既有的 RBAC、密级、租户隔离、审计、合规约束
- 模型/Prompt/Workflow 全部可配置、可灰度、可回滚
- 客户能直观演示"AI 介入了什么"——每条 AI 输出可追溯、可解释

### 1.2 范围内（In Scope）

- 9 项档案能力（见 §2 能力清单），分四期交付
- 与现有 `iam`、`audit`、`collection`、`repository`、`preservation`、`utilization` 模块的整合
- 知识库 L1 元数据全量 + L4 业务规则静态 + L2 OCR 全文（P3 接入）
- 前端 4 个主要触点：AI 主页 `/ai`（独立全屏）/ 审核队列 / 评测中心 / AI 审计

### 1.3 范围外（Out of Scope，本期不做）

- 知识库 L3（原始附件文件嵌入）、L5（利用记录嵌入）—— 留接口预留位
- AI 完全自主决策的写操作 —— 必须经 HITL 闸门
- 多 Dify 实例联邦 —— 一个 Dify 实例服务所有租户，租户级隔离靠独立 Dataset + App 命名约定
- 业务方在 Dify UI 自助改 Workflow —— Dify 配置走 Git 同步，运营不直接动 UI

---

## 2. 能力清单与风险分级

按"价值递增 + 风险递增"组织。颜色代表落地难度：🟢 低 / 🟡 中 / 🔴 高。

| 编号 | 能力 | 难度 | 性质 | 真实可期效果 | 上线形态 |
|---|---|---|---|---|---|
| ① | RAG 智能问答 | 🟢 | 读 | Recall@5 ≥ 85% | 完整 |
| ④ | 自然语言检索 | 🟢 | 读 | 意图准确率 ≥ 85% | 完整 |
| ⑧ | 知识库交互管理 | 🟢 | 读+写 | CRUD 包壳 | 完整（写侧走 patch） |
| ② | 档案自动挂接 | 🟡 | 写 | 类目级 90%+，父档级靠 HITL | 完整（patch + 审核） |
| ③ | AI 自动编目 | 🟡 | 写 | 软字段 70-85%，硬字段交 NoRule | 完整（patch + 审核） |
| ⑤ | 档案摘要/综述 | 🟡 | 读 | 强制引用，无证据拒答 | 完整 |
| ⑥ | 四性检测辅助 | 🔴 | 读 | 风险标记，不下判定 | 建议态 |
| ⑦ | 审稿/拟稿 | 🔴 | 读 | 草稿不替代正式签发 | 建议态 |
| ⑨ | 跨档案关联分析 | 🔴 | 读 | 实体消歧不可靠 | 建议态 |

**风险红线**：🔴 三项永不自动落库，只在 UI 中作为"AI 建议卡片"呈现，
用户需要采纳时手动复制到正式表单或触发审批流。

---

## 3. 架构总览（γ 分层分工）

### 3.1 分层

```
┌─────────────────────────────────────────────────────────┐
│ 前端 admin-web                                           │
│  独立 AI 主页 /ai  /  审核队列 /admin/ai/patches         │
│  评测中心 /admin/ai/eval  /  AI 审计 /admin/ai/audit     │
└────────────────────────────┬────────────────────────────┘
                             │ SSE / fetch
                             ▼
┌─────────────────────────────────────────────────────────┐
│ 后端 app/modules/ai/   ── "AI Gateway"                   │
│  会话编排  │  工具回调  │  知识库管线                     │
│  - 场景路由   - 档案 CRUD    - L1 同步                   │
│  - SSE 透传   - NoRule 生号  - L4 静态                   │
│  - 身份注入   - 检索代理     - L2 OCR                    │
│  - 审计写入   - Patch 提交                               │
└────────────┬──────────────────────────────┬─────────────┘
             ▼                              ▼
   ┌────────────────────┐         ┌─────────────────────┐
   │  Dify (官方独立)   │         │  PG + ES + 向量库   │
   │  主 Chatflow       │         │ （现有基础设施）    │
   │  + N 个 Workflow   │         └─────────────────────┘
   │  + 租户独立 Dataset│
   └────────────────────┘
```

### 3.2 五条不可破坏的设计约束

1. **身份从不信任 Dify**：所有写操作的 `user_id / tenant_id / 密级` 由后端从 JWT 取，
   注入到 Tool 调用上下文，Dify 拿不到也篡改不了。
2. **写操作走 `ai_patch`**：AI 不直接 INSERT/UPDATE 档案表，产出 staging patch，
   HITL 闸门按租户配置决定 auto / review / manual 三档处理路径。
3. **检索强制后端代理**：Dify 不直连 ES/向量库，必须调后端 `/internal/ai/retrieve`，
   后端按用户密级/租户/类目权限注入 filter，绝不信任 Dify 传入的过滤参数。
4. **每个 AI 输出都带引用**：问答/摘要必须挂 `evidence_chunks[]`，无证据则拒答。
   引用 chunk 必须在用户权限范围内，越权引用整段答案被替换为"出处校验失败"。
5. **Eval Harness 是上线门禁**：每个能力必须有黄金集 + 准确率阈值。
   Workflow 升版必须先过 Eval；驳回的 patch 自动进"待标注池"反哺黄金集。

### 3.3 命名空间与错误码

- 后端模块：`backend/app/modules/ai/`（现有，扩展）+ `ai_patch/` + `ai_eval/`
- Dify 应用命名：`{tenant_code}-archive-agent`（主）+ `{tenant_code}-wf-{capability}-v{n}`
- Dataset 命名：`{tenant_code}-meta` / `{tenant_code}-rules` / `{tenant_code}-ocr`
- 错误码段：**6000 段**专属 AI 模块
  - 6001 模型不可用 / 6002 检索越权 / 6003 patch 冲突 / 6004 评测未达标
  - 6005 引用校验失败 / 6006 Workflow 版本不一致 / 6007 Tool 鉴权失败
  - 6008 场景未启用 / 6009 租户配额超限

---

## 4. 分期路线图

| 期 | 主题 | 风险 | 关键交付 | 上线门禁 |
|---|---|---|---|---|
| **P1** | 地基 | 🟢 | Gateway / 知识库 L1+L4 / 审计 / Eval 骨架 / 多场景路由 / 演示型 UI 壳 | Gateway 健康 + 问答 30 条种子 Recall@5 ≥ 80% |
| **P2** | 读能力 | 🟢 | ① 问答升级 / ④ NL 检索 / ⑤ 摘要 / ⑧ 读侧 | 问答 Recall@5 ≥ 85% / NL 检索意图 ≥ 85% / 摘要引用 100% |
| **P3** | 写能力 | 🟡 | ② 自动挂接 / ③ 自动编目 / ⑧ 写侧 / `ai_patch` 审核队列 / L2 OCR | 自动挂接类目级 ≥ 90% / 编目软字段 ≥ 80%（参考值，最终调） |
| **P4** | 建议态 | 🔴 | ⑥ 四性建议 / ⑦ 拟稿 / ⑨ 关联建议（永不自动落库） | 用户接受率 ≥ 30%（参考） |

### 4.1 P1 — 地基期

不放任何"完整能落地"的用户能力，但客户能直观看到一套结构。

- 后端 `ai/` 扩展：场景路由器、Tool 回调骨架、检索代理（强制 filter）
- 知识库管线：L1 元数据全量 + 增量同步到对应租户 Dataset；L4 业务规则手动导入
- 多场景前端壳：`/ai` 独立页内 6 个场景 Tab 都出，未实装的点击渲染"敬请期待"占位卡片
- 审计扩展：`ai_chat_query` / `ai_tool_call` / `ai_patch_*` / `ai_eval_run` 四类
- Eval Harness 骨架：黄金集表、CLI 执行器、`pytest -m eval` 接入；问答场景接入 30 条种子
- 错误码 6000 段定义
- 灰度开关：`AI_ENABLED_CAPABILITIES` 配置，能力逐个放开
- **演示亮点**：引用 chip 必须实装（点击跳档案详情）、5 个 AI 菜单实装入口

### 4.2 P2 — 读能力期

用户在聊天框里能问出价值，每条答案都带可点击的档案出处。

- ① RAG 问答升级：场景化 Prompt、强制引用、拒答策略
- ④ NL 检索：自然语言 → ES 结构化查询，结果落到现有档案列表组件，**不另起页面**
- ⑤ 摘要/综述：基于检索结果集生成专题综述，每段挂引用
- ⑧ KB 管理（读侧）：列出已索引全宗 / 是否在知识库 / 重建状态查询
- 多场景切换 UX 固化（模型档位选择上线）
- 黄金集扩展到每能力 100+ 条；Eval 准确率门禁纳入 CI

### 4.3 P3 — 写能力期

项目最大卖点，也是最危险的一期。审核队列是核心交互。

- `ai_patch` 模块：staging 表、可逆 diff 存储、提交/驳回 Service、审核队列 API
- 前端审核队列页：字段级 diff、批量勾选、通过/驳回/部分修改、引用列表
- ② 档案自动挂接：单条 + 批量两种入口，都走 patch；HITL 闸门可配 auto/review/manual
- ③ AI 自动编目：OCR 触发 → 软字段抽取 → NoRule 生硬字段 → 写入 patch
- L2 OCR 索引管线：先支持文本型 PDF/DOCX，扫描件下一阶段
- 黄金集扩展到每写能力 200+ 条；"专家标注界面"批量造数据
- 用户驳回 patch 自动入"待标注池"

### 4.4 P4 — 建议态期

红色高风险能力，永不自动落库。

- ⑥ 四性检测辅助：档案详情页加"AI 风险提示"侧栏，标红可疑点
- ⑦ 拟稿：开放鉴定意见 / 销毁建议 / 利用报告草稿，落到"我的草稿夹"
- ⑨ 跨档案关联：检索时附"可能相关的档案"卡片，纯建议
- 引入"专家打分"评测机制（主观成分大）
- 用户接受率作为质量指标，过低能力下线

---

## 5. 后端模块结构

### 5.1 模块拓扑

```
backend/app/modules/
├── ai/                        现有，扩展
│   ├── api/
│   │   ├── routes_chat.py     现有 /chat 升级：增加 scenario / model_tier
│   │   ├── routes_retrieve.py 新增 /internal/retrieve（Dify 回调，service-token）
│   │   ├── routes_tool.py     新增 /internal/tool/* （Dify Workflow 回调）
│   │   ├── routes_kb.py       新增 /kb/* （知识库状态、重建触发）
│   │   └── routes_admin.py    新增 /admin/audit、/admin/eval 后台
│   ├── services/
│   │   ├── dify_service.py    现有，扩展为多 App 路由
│   │   ├── scenario_router.py 场景 ↔ Dify App 映射 + 灰度开关
│   │   ├── retrieval_service.py 检索代理，注入权限 filter
│   │   ├── tool_dispatch.py   Tool 回调入口，验签 + 身份恢复
│   │   ├── kb_sync_service.py L1/L2/L4 同步管线
│   │   └── citation_validator.py 引用权限校验
│   ├── schemas/
│   ├── tasks/                 kb_sync_task / eval_run_task
│   └── models/                ai_scenario / ai_session
│
├── ai_patch/                  新增（P1 建表，P3 实装）
│   ├── api/routes_patch.py    审核队列 API
│   ├── services/
│   │   ├── patch_service.py   create / approve / reject / preview-diff
│   │   ├── catalog_patch.py   ③ 自动编目 patch
│   │   └── attach_patch.py    ② 自动挂接 patch
│   ├── schemas/patch.py
│   └── models/ai_patch.py     staging 表 + 状态机
│
└── ai_eval/                   新增
    ├── api/routes_eval.py
    ├── services/
    │   ├── runner.py          黄金集执行器
    │   ├── metrics.py         准确率/召回率/引用覆盖率
    │   └── annotation.py      专家标注辅助
    ├── schemas/eval.py
    └── models/
        ├── golden_set.py
        ├── eval_run.py
        └── annotation.py
```

### 5.2 三条不可破坏的边界

1. **Dify 永不直连 DB/ES/向量库**——所有数据访问必须经 `ai/api/routes_retrieve.py`
   和 `routes_tool.py`，凭 service-token + 用户身份 header 进来。
2. **Tool 回调必须验签 + 恢复用户身份**——Dify 调过来时带 `X-User-Token`
   （短期 JWT，5min TTL，由后端 chat 入口签发），后端验签后用此身份执行业务，
   RBAC 全套走一遍。
3. **`ai_patch` 是唯一的 AI 写库通道**——服务层 lint 规则禁止 `ai/*` 代码直接调
   `archive_service.create/update`，必须经 patch 模块。

### 5.3 跨模块依赖

- `ai/` 依赖：`iam`（用户/租户/密级）/ `audit`（写日志）/ `repository`（只读取档案元数据填 prompt）
- `ai_patch/` 依赖：`ai`（接收 patch 产出）/ `repository`（提交时落库）/ `audit`
- `ai_eval/` 依赖：`ai`（调被测能力）；**不依赖 `ai_patch`**（评测看产出，不落库）

---

## 6. Dify 应用拓扑

### 6.1 每租户的 App 组织

每个租户在 Dify 内有：

- **1 个主 Chatflow App**：`{tc}-archive-agent`，会话入口 + 意图识别 + 路由分发
- **N 个能力 Workflow**：`{tc}-wf-{capability}-v{n}`，每能力一个
- **3 个 Dataset**：`{tc}-meta` / `{tc}-rules` / `{tc}-ocr`

主 Chatflow 固定 5 个节点（便于 Eval 模板化注入）：

1. **Start**：接 `{query, scenario_hint, model_tier, X-User-Token}`
2. **Intent Router**：LLM 判意图输出 `scenario_code`；前端显式选场景则跳过
3. **Capability Dispatcher**：HTTP Request 回调后端 `/internal/tool/dispatch`，
   **不直接调子 Workflow**（路由权在后端，可灰度/降级）
4. **RAG Fallback**：未命中能力时走内置 Knowledge Retrieval（L1+L4 Dataset）
5. **Answer Assembler**：统一成 `{answer, citations, patch_ref?}` 三段式

### 6.2 能力 Workflow 的统一契约

让 Eval 能模板化跑，所有 `wf-*` 遵守：

- **输入**：`{user_token, scenario_code, query, context_archive_ids?, extra_params?}`
- **输出**：
  - 读类：`{answer, citations[], confidence}`
  - 写类：`{patch_payload, citations[], confidence}` —— Workflow 本身**不落库**，
    `patch_payload` 由 `tool_dispatch.py` 写入 `ai_patch`
  - 拟稿类：`{draft_text, citations[], suggested_target}` —— 文本回聊天，不落库

### 6.3 模型路由：用户视角 = 3 档

用户在聊天面板上看到 3 个档位，不直接选 LLM 品牌：

| 档位 | 后端实际（示例，可调） | 适用 |
|---|---|---|
| **快** | Qwen-Turbo / Haiku 级 | 简单问答、检索改写、轻量摘要 |
| **准** | Qwen-Max / Sonnet 级 | 编目抽取、四性建议、复杂综述 |
| **思考** | DeepSeek-R1 / Opus 级 | 跨档案关联、拟稿、需推理场景 |

档位 → 实际模型 ID 的映射在 `ai_scenario` 表里维护，前端只看到三档。
换模型不动前端、不动 Workflow，只改配置。

### 6.4 Prompt / Workflow 版本管理

- `backend/app/modules/ai/dify_config/` 目录存每个 App / Workflow 的导出 YAML
- 部署脚本 `scripts/dify_sync.py` 把 YAML 推到目标 Dify 实例
- 黄金集与 Workflow 版本绑定，升版必须先过 Eval

---

## 7. 横切关注点

### 7.1 HITL 三档闸门

每个 AI 写能力配置 3 个开关位（租户管理员后台设置）：

- **auto**：AI 出 patch 直接 approve，落库
- **review**：AI 出 patch 进审核队列，等人点（默认）
- **manual**：AI 出 patch 但带"高风险"标记置顶，必须二审签

| 能力 | 默认闸门 |
|---|---|
| ② 自动挂接 | review |
| ③ 自动编目 | review |
| ⑧ KB 加文档 | review |
| ⑧ 重建索引 | manual |
| 批量任务 | manual |

### 7.2 引用强制

- Dify Workflow 在 Answer Assembler 节点硬约束：无 `citations[]` 不出口
- 后端 `citation_validator.py` 二次校验：引用 chunk_id 必须在用户密级/租户/类目权限范围内，
  越权引用整段答案替换为"出处校验失败，已上报"
- 前端无引用 chip 的答案置灰并标"未引证"

### 7.3 审计扩展

新增 4 个动作码：

- `ai_chat_query`（现有，保留）
- `ai_tool_call`：每次 Dify → 后端 Tool 回调
- `ai_patch_create / approve / reject`：patch 全生命周期
- `ai_eval_run`：每次评测

所有 AI 动作审计都带 `scenario_code / model_tier / workflow_version / dify_message_id`，
可端到端追溯。

### 7.4 Eval Harness 运营节奏

- 每能力一个 `golden_set` 表，条目 `{input, expected_output_or_rubric, tags}`
- 每次 Workflow 改版 / 模型切换 / Prompt 调整 → 触发 `eval_run`，
  达不到阈值自动回滚 Workflow 版本
- 评测中心页面：算法工程师看准确率趋势 / 标注员录入新条目
- P3 起：用户驳回的 patch 自动入"待标注池"，专家审后转黄金集——
  **驳回是最便宜的数据来源**

### 7.5 权限/安全清单

| 攻击面 | 防御 |
|---|---|
| Dify 被攻破，伪造 user 调 Tool | Tool 入口验 `X-User-Token`（5min TTL），过期拒绝 |
| 用户问"导出别租户档案" | 检索代理强制注 `tenant_id` filter，忽略 Dify 传入参数，只信 JWT |
| 低密级用户问绝密内容 | 引用校验拦截：`secret_level > user.secret_level` 的 chunk 整段丢弃 |
| AI 诱导越权（"调用 delete_archive"） | Tool 接口 RBAC 一道不少，AI 没权限调不动 |
| Patch 被人在后台手改 | `ai_patch.payload_hash`，approve 时校验未篡改 |

---

## 8. 前端 UX

> **核心原则**：AI 是这个项目的招牌能力，必须有独立全屏页承载，**绝不做抽屉/浮窗形态**。
> 已有 `frontend/admin-web/pages/ai/index.vue` 的 ChatGPT 风骨架作为基础，
> 在它上面演进，不另起新页面。

### 8.1 四个主要触点

1. **AI 主页** `/ai`（独立全屏，唯一对话入口）
   - 左侧：历史会话列表 + "新对话"按钮（已有骨架）
   - 顶栏：场景 Tab（问答 / 检索 / 摘要 / 挂接 / 编目 / 四性 / 拟稿 / 关联）+ 模型档位徽章（快/准/思考）
   - 中央：消息流 —— AI 气泡下方挂引用 chip 行，点 chip 跳档案详情；写类场景下气泡内嵌"已生成 Patch 草案 #N"卡片，点击跳审核队列
   - 底部输入区：输入框 + 上下文 chips（自动捕获从其他页面跳入时携带的 archive_id）+ 模型档位下拉
   - 右侧（可折叠）：当前场景说明 + 示例提示词 + 知识库范围指示

2. **AI 操作审核队列页** `/admin/ai/patches`
   - 列表：场景 / 提出时间 / 提出人 / 状态 / AI 置信度
   - 详情侧栏：字段级 diff（左原值 / 右 AI 建议）+ 引用列表 + 通过/驳回/修改

3. **AI 评测中心页** `/admin/ai/eval`
   - 准确率趋势图（按能力 / 按 Workflow 版本）
   - 黄金集管理（增删改、批量导入 CSV）
   - "驳回学习池"：转黄金集

4. **AI 操作审计页** `/admin/ai/audit`
   - 复用现有审计列表组件，加 AI 专属过滤器（scenario / model_tier / patch_id）

### 8.2 业务页面 → AI 的跳转模式

业务页面（档案详情 / 类目管理 / 全宗列表等）允许出现"在此页打开 AI"按钮，
但**点击行为是跳转到 `/ai`** 并通过 query 把上下文（`archive_id` / `category_id` 等）带过去，
AI 页加载时自动塞进底部上下文 chips。**不在原页面就地弹窗**。

### 8.3 视觉语言 —— AI 科技感

档案系统其他模块沿用 daisyUI + Semi 的稳重视觉，但 `/ai` 页面要明显"未来感"区隔，
让用户一进来就感受到这是"AI 的地盘"：

- **色调**：深色优先，主色用青蓝/紫色渐变（`oklch(var(--p))` 系），背景大面积近黑或深蓝灰
- **质感**：玻璃拟态（backdrop-blur）+ 半透明卡片 + 微光描边（border 用 oklch 半透明色）
- **动效**：消息流入有打字机/淡入；模型档位切换时徽章有发光过渡；
  "AI 思考中"用流光 / 粒子 / 呼吸光环（非传统 Spinner）
- **字体**：标题用稍未来感的字号节奏（大、紧凑），正文保持可读
- **强调元素**：引用 chip 用渐变描边；Patch 草案卡片用"半透明 + 内阴影"营造"待办悬浮"感
- **空态**：6 个场景的"敬请期待"卡片做成"AI 能力解锁中"的科技感占位（带进度条 / 倒计时 / 模糊预览）
- 整体参考方向：Linear 的暗色 + Vercel AI Playground + ChatGPT 桌面端，三者融合

视觉实施时调用 `ui-ux-pro-max` Skill 选具体风格组合（glassmorphism + 深色 + 渐变光晕组合），
最终调色板/字体配对/动效细节在实施时确定。

### 8.4 P1 占位规则

- `/ai` 页内 6 个场景 Tab 都出，未实装点击渲染"AI 能力解锁中 · 预计 P? 上线"科技感占位卡片
- 审核队列页空态："暂无待审 AI 操作"（同样深色科技感设计）
- 评测中心 mock 一张折线图 + "暂未对接评测数据"
- 审计页 P1 起就跑真数据（问答日志）

### 8.5 写代码前的约束（项目级规则）

写任何 `.vue` 文件前必须先加载本项目前端规范 Skill，强制 Tailwind，
能用 Tailwind 的地方不允许一行 scoped CSS；
`/ai` 页的"科技感"通过 Tailwind 任意值 + `oklch()` + Semi 设计 token 实现，不引入新组件库。

---

## 9. 关键设计决定记录

> 这一节是把"我们讨论过的取舍"列下来，避免将来忘了为什么这么定。

| 决定 | 选择 | 理由 / 拒绝的方案 |
|---|---|---|
| Dify 与后端分工 | γ：Dify 中、后端中 | α（Dify 厚）测试和事务难，β（后端厚）失去 Dify 价值 |
| 多租户隔离 | 一租户一 Dataset（路线 a） | 客户租户少（≤3），物理隔离最稳 |
| 知识库范围 | 本期 L1 + L4，L2 分批，L3/L5 预留 | L3 体量太大、L5 涉个人信息，本期不值得 |
| AI 写操作形态 | staging patch + HITL 审核队列 | **拒绝**降级到 Copilot 表单预填——客户认为人工敲定成本可控，AI 通道定位是"方便+智能"不是"严谨"；想准确就走原业务界面 |
| 模型选择 UX | 用户看到"快/准/思考"3 档 | 比让用户选 GPT/Claude/Qwen 品牌更友好；换模型不动前端 |
| 主 Chatflow 结构 | 1 主 + N Workflow，由后端 dispatch | 替代方案"每能力独立 App"碎且难管 |
| AI 前端入口形态 | 独立全屏页 `/ai`，深色科技感 | **拒绝**抽屉/浮窗：太"小家子气"，承载不了 AI 作为项目核心卖点的分量；业务页跳转走 `/ai?archive_id=...` 带上下文 |
| 9 项能力组织 | 4 期交付，红色 3 项永远建议态 | 一次性全做风险过高 |
| Dify 配置管理 | Git + 同步脚本（非 UI 改） | 客户场景无运营自助改 Workflow 诉求 |
| 错误码段 | 6000 段专属 AI | 与现有 1000-9999 段不冲突 |

---

## 10. 风险与缓解

| 风险 | 缓解 |
|---|---|
| LLM 幻觉编造档案内容 | 强制引用 + 拒答策略 + `citation_validator` 越权拦截 |
| 审核员"批量盖章"导致 HITL 形同虚设 | 审核队列默认按 AI 置信度倒序，低置信置顶；定期抽查通过率 |
| Dify 升级导致 Workflow 不兼容 | YAML 配置纳入 Git，升级前先在测试 Dify 实例跑 Eval |
| 模型供应商断供 | 模型档位映射可热切换，三档各预留 ≥2 个备选 |
| 知识库重建期间检索不可用 | `kb_sync_service` 走双 buffer：新 Dataset 重建完成后切换别名 |
| OCR 质量差导致编目错抽 | P3 先只接文本型 PDF/DOCX，扫描件 OCR 留 P3+ |
| 评测数据不足导致门禁失效 | P3 起强制"驳回入池"机制，按月扩黄金集 |
| 高密级档案被 AI 摘要泄露 | 引用校验拦截 + 摘要拒答（在 Prompt 里硬约束密级限制） |

---

## 11. 附录

### 11.1 错误码（6000 段）

| 码 | 含义 |
|---|---|
| 6001 | AI 模型不可用 / 上游超时 |
| 6002 | 检索越权（tenant/密级/类目越界） |
| 6003 | Patch 状态冲突（已被处理） |
| 6004 | Eval 未达标，Workflow 上线被阻 |
| 6005 | 引用校验失败 |
| 6006 | Workflow 版本不一致 |
| 6007 | Tool 鉴权失败（X-User-Token 缺失/过期） |
| 6008 | 场景未启用 / 灰度未放开 |
| 6009 | 租户 AI 配额超限 |

### 11.2 关键配置项

| 配置项 | 含义 | 默认 |
|---|---|---|
| `DIFY_BASE_URL` | Dify API 地址 | （现有） |
| `DIFY_API_KEY` | Dify 主 App API Key | （现有） |
| `AI_ENABLED_CAPABILITIES` | 启用的能力码列表，逗号分隔 | `qa`（P1） |
| `AI_DEFAULT_MODEL_TIER` | 默认模型档位 | `准` |
| `AI_USER_TOKEN_TTL_SECONDS` | Tool 回调短 token 有效期 | `300` |
| `AI_EVAL_BLOCK_ON_REGRESSION` | 评测回归是否阻断 Workflow 升级 | `true` |
| `AI_PATCH_DEFAULT_GATE` | patch 默认闸门 | `review` |
| `AI_CITATION_REQUIRED` | 是否强制引用 | `true` |

### 11.3 命名约定

- Dify App：`{tenant_code}-archive-agent` / `{tenant_code}-wf-{capability}-v{n}`
- Dify Dataset：`{tenant_code}-{meta|rules|ocr}`
- DB 表：`ai_scenario` / `ai_session` / `ai_patch` / `golden_set` / `eval_run` / `annotation`
- 错误码段：6000-6999

### 11.4 与既有规则的衔接

- 档案字段命名遵循 DA/T 拼音缩写（DH/QZH/TM/ND/MJ/BGQX…）—— AI patch 字段名一律用此规范
- 软删除是底线 —— patch 提交时只动业务字段，从不真删除
- 所有 I/O 异步 —— `ai/*` 全部 async，httpx 异步客户端
- 响应统一 `ResponseModel(code, data, message)` 信封
- RBAC 装饰器 `require_permissions(*perms)` 在每个 Tool 回调入口必加

---

## 12. 下一步

本设计稿冻结后：

1. P1 任务拆解到 sprint 维度（不写 plan 文件，直接进代码）
2. 起手三件事并行：
   - 数据库迁移：`ai_scenario` / `ai_patch` / `golden_set` / `eval_run` 表
   - Dify 主 Chatflow YAML 定义并推到测试实例
   - 前端 5 个菜单入口的占位 UI
3. 完成 P1 后请求用户验收演示，决定是否进 P2

---

**文档版本**：v1.0（2026-05-11）
**评审状态**：待 Hikari 审阅
