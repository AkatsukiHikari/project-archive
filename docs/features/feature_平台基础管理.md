# Feature: 平台基础管理 整改方案

> 状态：待实施  
> 优先级：高  
> 涉及范围：Backend 数据初始化 + Frontend 全页面重新设计

---

## 一、问题诊断

### 1.1 后端问题 — 无初始数据，系统启动即死
- **无种子脚本**：`lifespan.py` 只初始化 ES 索引，无任何数据库初始数据逻辑
- **超级管理员缺失**：首次部署后数据库为空，无法登录，前端所有 admin 逻辑均无意义
- **无默认租户**：用户/角色/组织均依赖 `tenant_id`，无租户则无法创建任何数据
- **无默认角色与菜单**：RBAC 体系需要角色与菜单数据才能运作，当前全靠手动录入

### 1.2 前端问题 — 视觉质量差，交互体验差
- **重复的租户选择栏**：每个页面顶部都有相同的租户 Select，冗余且割裂
- **无页面头部层次**：缺少标准的 `页面标题 + 描述 + 操作按钮` 头部结构
- **表格无样式增强**：空状态无图示、无分页美化、无行操作 hover 效果
- **Modal 表单薄弱**：字段简单、无分组、无验证提示美化
- **各页面风格不统一**：部分用 `Card`，部分用裸 `div`

---

## 二、整改目标

### 后端目标
1. 实现 **幂等种子脚本** `backend/app/scripts/seed.py`，一键初始化全套基础数据
2. 在 `lifespan.py` 启动时自动执行 seed（生产环境可通过环境变量跳过）
3. 种子数据覆盖：默认租户 → 超级管理员用户 → 默认角色 → 完整菜单树

### 前端目标
1. 统一页面布局：`页面头` + `工具栏` + `内容区`，遵循 `admin.vue` 侧边栏+tabs 约束
2. 用全局 `TenantContext`（Pinia store）统一管理当前租户，消除各页面重复选择栏
3. 重设计5个核心页面：用户、角色、组织、租户、菜单

---

## 三、后端实施方案

### Phase B1 — 种子脚本 `backend/app/scripts/seed.py`

**种子数据顺序（有依赖关系）：**

```
1. 默认租户（system）
   ├── code: "system"
   ├── name: "系统默认租户"
   └── is_active: true

2. 超级管理员用户
   ├── username: "admin"
   ├── email: 从 .env ADMIN_EMAIL 读取（默认 admin@sams.local）
   ├── password: 从 .env ADMIN_PASSWORD 读取（必填，启动时校验）
   ├── is_superadmin: true
   ├── is_active: true
   └── tenant_id: → 默认租户

3. 内置角色（全局，tenant_id=NULL）
   ├── superadmin  (code: "superadmin",  绑定所有菜单)
   ├── admin       (code: "admin",       绑定管理类菜单)
   └── viewer      (code: "viewer",      只读菜单)

4. 默认菜单树（对应实际 admin 路由）
   ├── 平台基础管理 (type=GROUP)
   │   ├── 租户管理       /admin/tenants
   │   ├── 组织架构       /admin/organizations
   │   ├── 用户管理       /admin/users
   │   ├── 角色与权限     /admin/roles
   │   └── 菜单与权限     /admin/menus
   ├── 安全与集成 (type=GROUP)
   │   ├── SSO 集成       /admin/sso
   │   └── 审计日志       /admin/audit
   └── (其余业务子系统菜单由各子系统模块自行注册)

5. 超级管理员 ← 绑定 superadmin 角色
```

**幂等保证**：每个实体先 `SELECT` 检查是否存在，存在则跳过，不存在才 `INSERT`。

**实现文件**：
```
backend/app/scripts/
└── seed.py           # 独立可运行：uv run python -m app.scripts.seed
```

**lifespan 集成**：
```python
# app/bootstrap/lifespan.py
from app.scripts.seed import run_seed
await run_seed()  # 幂等，生产环境设 SKIP_SEED=true 跳过
```

**`.env` 新增变量**：
```
ADMIN_EMAIL=admin@sams.local
ADMIN_PASSWORD=           # 必填，启动时若为空则报错
SKIP_SEED=false           # 生产环境设 true 跳过
```

### Phase B2 — 档案到期预警 API（`/api/v1/archives/expiry-summary`）

为首页个人面板的到期预警 widget 提供真实数据：

```python
GET /api/v1/archives/expiry-summary
Response: {
  "urgent": 8,    # 7天内
  "soon": 23,     # 30天内  
  "pending": 67   # 90天内
}
```

---

## 四、前端实施方案

### 全局设计规范（admin 子系统通用）

**页面标准结构**：
```
┌─ 页面头 PageHeader ─────────────────────────────────────────┐
│  [图标] 页面标题          [描述文字]         [主操作按钮]      │
└──────────────────────────────────────────────────────────────┘

┌─ 工具栏 Toolbar ────────────────────────────────────────────┐
│  [搜索框]  [筛选项]                     [次操作] [更多操作]   │
└──────────────────────────────────────────────────────────────┘

┌─ 内容区 Content ────────────────────────────────────────────┐
│  表格 / 树形 / 详情面板                                       │
└──────────────────────────────────────────────────────────────┘
```

**租户上下文**：在 `admin.vue` layout 的顶栏（SystemHeader）中加入租户选择器，保存至 Pinia `useAdminStore`，各子页面直接读取，不再重复渲染。

**新增共享组件**：
```
frontend/admin-web/components/admin/
├── PageHeader.vue         # 标准页面头：标题+描述+操作
├── TenantSelector.vue     # 顶部租户切换（仅在 admin layout header 中使用）
└── StatusBadge.vue        # 启用/禁用状态徽章
```

---

### Phase F1 — 用户管理页 `/admin/users`

**当前问题**：裸表格，无搜索过滤，Modal 字段简单，无头像/角色展示。

**重设计方案**：

```
PageHeader: 用户管理 | 管理所有租户用户账号 | [+ 新增用户]

Toolbar: [搜索: 用户名/姓名/邮箱] [状态: 全部/启用/禁用] [部门: 下拉]

Table 列设计:
┌────────────────────────────────────────────────────────────┐
│ 用户       │ 邮箱  │ 所属部门 │ 角色       │ 状态  │ 操作   │
│ [头像+姓名] │      │          │ [角色Tags] │ 开关  │ 编辑   │
└────────────────────────────────────────────────────────────┘

Modal (抽屉 Drawer 替代 Modal, 更宽敞):
├── 基本信息组: 用户名、真实姓名、邮箱、手机
├── 归属组: 所属租户、所属部门
├── 权限组: 角色分配（多选 Tag 选择器）
└── 安全组: 初始密码、账号状态
```

### Phase F2 — 角色与权限页 `/admin/roles`

**当前问题**：左右分栏布局基本可用，但菜单权限配置 UI 缺失/简陋。

**重设计方案**：

```
PageHeader: 角色与权限 | RBAC 角色配置及菜单权限分配 | [+ 新增角色]

三栏布局 (3-col):
┌─ 角色列表 (col-3) ─┬─ 角色详情 (col-4) ─┬─ 权限配置 (col-5) ─┐
│ 搜索                │ 角色名称            │ 菜单权限树          │
│ ─────────────────  │ 描述                │ [全选] [反选]       │
│ ● superadmin       │ 成员数量            │ ─ 平台基础管理       │
│ ● admin            │ 创建时间            │   ☑ 租户管理        │
│ ● viewer           │ [编辑] [删除]       │   ☑ 用户管理        │
│ + 新增角色          │                    │   ☑ 角色配置        │
└────────────────────┴────────────────────┴────────────────────┘
```

### Phase F3 — 组织架构页 `/admin/organizations`

**当前问题**：树形组件基础可用，但节点操作入口差，成员列表无样式。

**重设计方案**：

```
PageHeader: 组织架构 | 部门层级管理与人员归属 | [+ 新增顶级部门]

两栏布局 (2-col, 1:2):
┌─ 组织树 (col-4) ────────┬─ 部门详情 (col-8) ─────────────────┐
│ 搜索部门                 │ [部门名称]  [编辑] [新增子部门] [删除]│
│ ─────────────────────   │ ──────────────────────────────────  │
│ ▼ 系统默认租户            │ Tabs: [部门成员] [子部门]            │
│   ▶ 办公室               │                                     │
│   ▼ 业务部               │ 成员列表: 头像+姓名+职位+操作         │
│     ▶ 档案科             │                                     │
└──────────────────────────┴─────────────────────────────────────┘
```

### Phase F4 — 租户管理页 `/admin/tenants`

**当前问题**：未详细查看，预计与其他页面同等问题。

**重设计方案**：

```
PageHeader: 租户管理 | 多租户隔离配置 | [+ 新增租户]

Table 列:
┌────────────────────────────────────────────────────────────┐
│ 租户名称    │ 编码    │ 用户数 │ 创建时间 │ 状态  │ 操作   │
└────────────────────────────────────────────────────────────┘

点击租户名: 侧抽屉展示租户详情 + 关联组织/用户统计
```

### Phase F5 — 菜单与权限页 `/admin/menus`

**当前问题**：菜单树管理是整套系统最复杂的页面，当前实现未知质量。

**重设计方案**：

```
PageHeader: 菜单与权限 | 系统菜单树及按钮级权限配置 | [+ 新增菜单]

两栏布局 (2-col):
┌─ 菜单树 (col-5) ──────────┬─ 菜单详情表单 (col-7) ──────────┐
│ 可拖拽排序的树形组件        │ 菜单类型: [目录] [页面] [按钮]    │
│ ▼ 平台基础管理             │ 菜单名称, 路由, 图标              │
│   ▶ 租户管理               │ 排序号, 是否可见                  │
│   ▶ 用户管理               │ 权限码 (按钮级)                   │
│ ▼ 安全与集成               │ [保存] [取消]                     │
└────────────────────────────┴─────────────────────────────────┘
```

---

## 五、实施顺序

```
优先级 P0 (阻断性，必须先做):
  B1 - 种子脚本            # 没有数据，前端一切皆空

优先级 P1 (核心页面):
  F0 - 共享组件 + TenantContext Pinia store
  F1 - 用户管理重设计
  F2 - 角色与权限重设计
  F3 - 组织架构重设计

优先级 P2 (次要页面):
  F4 - 租户管理重设计
  F5 - 菜单与权限重设计

优先级 P3 (补充):
  B2 - 档案到期预警 API    # 为首页 widget 提供真实数据
```

---

## 六、风险点

| 风险 | 级别 | 缓解措施 |
|------|------|---------|
| seed 脚本非幂等导致重复数据 | HIGH | 每个实体先查后插，以 username/code 为唯一键 |
| ADMIN_PASSWORD 为空启动 | HIGH | lifespan 启动时若 seed 需运行则强制校验 |
| 删除租户级联删所有用户/角色 | MEDIUM | 软删除 + 禁止删除有用户的租户 |
| 菜单树拖拽排序并发冲突 | LOW | 乐观锁 + sort_order 字段 |

---

## 七、平台管理首页 Dashboard 重设计方案

> 状态：待商讨  
> 对应页面：`/admin/index`（`pages/admin/index.vue`）

---

### 7.1 当前问题

- 4 张静态 KPI 卡片，无图表，数据来自 `/v1/stats/dashboard` 但接口字段贫乏
- "系统状态" 卡片硬编码为 "正常"，没有真实数据
- 无任何 ECharts 可视化
- 无系统运维信息（DB/Redis/队列/存储健康状态）
- 无权限分层（管理员与超管看到内容相同）

---

### 7.2 目标效果

```
┌─ 欢迎栏 ─────────────────────────────────────────────────────────────┐
│  早上好，张三！今天是 2026-04-12  │  今日新增用户 +3  │  待处理 SIP 5条  │
└──────────────────────────────────────────────────────────────────────┘

┌─ KPI 卡片行（4 列）───────────────────────────────────────────────────┐
│  [超管] 活跃租户数  │  系统用户总数  │  [超管] 角色数  │  部门总数        │
│    趋势箭头 + 环比    │  活跃/总 比率  │   全局角色数    │  组织节点数      │
└──────────────────────────────────────────────────────────────────────┘

┌─ 图表区（左 2/3 + 右 1/3）────────────────────────────────────────────┐
│  ECharts 折线图：近 7 天每日活跃登录用户数          │ ECharts 环形图：     │
│  可切换 7天 / 30天，超管看全局，admin 看本租户       │ 审计操作模块分布      │
│                                                   │ IAM / ARCHIVE / AI  │
└────────────────────────────────────────────────────┴────────────────────┘

┌─ 底部双列 ────────────────────────────────────────────────────────────┐
│  左（[仅超管]）: 基础设施健康状态                  │ 右: 近10条审计日志流水 │
│  ● PostgreSQL  ✓ 3ms                             │  2026-04-12 14:33    │
│  ● Redis       ✓ 0.5ms                           │  admin 登录           │
│  ● RabbitMQ    ✓ 已连接  队列数 3                 │  admin 创建用户 zhangsan│
│  ● MinIO       ✓ 存储桶 5个                       │  ...                  │
│  ● Elasticsearch ✓ 集群 green                    │                       │
└──────────────────────────────────────────────────┴────────────────────┘
```

---

### 7.3 权限分层

| 区块 | superadmin | admin（非超管） | viewer |
|------|-----------|----------------|--------|
| KPI 活跃租户数 | ✓ 全平台 | ✗ 隐藏 | ✗ |
| KPI 用户数 | ✓ 全平台 | ✓ 本租户 | ✗ |
| KPI 角色数 | ✓ 全局角色 | ✗ 隐藏 | ✗ |
| KPI 部门数 | ✓ 全平台 | ✓ 本租户 | ✗ |
| 折线图用户趋势 | ✓ 全平台 | ✓ 本租户 | ✗ |
| 环形图审计分布 | ✓ | ✓ 本租户 | ✗ |
| 基础设施健康 | ✓ | ✗ 隐藏 | ✗ |
| 审计日志流水 | ✓ 全平台 | ✓ 本租户 | ✗ |

---

### 7.4 后端方案

#### 接口一：扩展 `GET /v1/stats/dashboard`

在现有 `DashboardStats` 模型上补充字段：

```python
class DashboardStats(BaseModel):
    # 原有
    active_tenants: int        # 超管可见，非超管返回 -1（前端据此隐藏）
    total_users: int
    active_users: int
    pending_sips: int
    # 新增
    total_roles: int           # 超管可见（-1 则隐藏）
    total_orgs: int            # 本租户或全平台
    new_users_today: int       # 今日新增用户数
```

#### 接口二：新增 `GET /v1/stats/user-activity?days=7`

从 `iam_audit_log` 表按天聚合，统计每天有登录行为的不重复用户数：

```python
# 查询：按 date(create_time) 分组，count distinct user_id，action='USER_LOGIN'
class DayActivity(BaseModel):
    date: str          # "2026-04-06"
    count: int         # 当天活跃用户数

class UserActivityResponse(BaseModel):
    days: int
    data: list[DayActivity]
```

权限：超管查全平台，admin 自动过滤 `tenant_id = current_user.tenant_id`

#### 接口三：新增 `GET /v1/stats/audit-distribution`

统计近 30 天各模块的操作次数，用于环形图：

```python
class ModuleCount(BaseModel):
    module: str        # "IAM" / "ARCHIVE" / "AI" / "SYSTEM"
    count: int

class AuditDistributionResponse(BaseModel):
    data: list[ModuleCount]
```

#### 接口四：新增 `GET /v1/stats/health`（仅超管）

真实 ping 各基础设施组件，毫秒级响应时间：

```python
class ComponentHealth(BaseModel):
    name: str           # "PostgreSQL"
    status: str         # "ok" | "error"
    latency_ms: float   # 响应耗时
    detail: str         # "连接池 5/20" / "集群状态 green" / 错误信息

class HealthResponse(BaseModel):
    components: list[ComponentHealth]
    checked_at: datetime

# 各组件检查方式：
# PostgreSQL:    await db.execute(text("SELECT 1"))
# Redis:         await redis.ping() + INFO memory
# RabbitMQ:      HTTP GET localhost:15672/api/overview (guest/guest)
# MinIO:         await minio_client.stat_object() or list_buckets
# Elasticsearch: await es.ping() + cluster.health()
```

**安全**：该接口通过 `require_permissions` 限制为 superadmin，非超管调用返回 403。

---

### 7.5 前端方案

#### ECharts 接入方式

使用 **`vue-echarts` v7 + `echarts` v5** 按需引入，避免打包全量 echarts：

```bash
pnpm add echarts vue-echarts
```

```typescript
// 按需引入，只打包用到的组件
import { use } from "echarts/core"
import { CanvasRenderer } from "echarts/renderers"
import { LineChart, PieChart } from "echarts/charts"
import { GridComponent, TooltipComponent, LegendComponent } from "echarts/components"
use([CanvasRenderer, LineChart, PieChart, GridComponent, TooltipComponent, LegendComponent])
```

图表组件通过 `markRaw` 规避 Vue 响应式代理 ECharts 实例。

#### 折线图：用户登录活跃趋势

- X 轴：日期（近7/30天）
- Y 轴：当日活跃用户数
- 交互：右上角切换 7天 / 30天；悬浮 Tooltip 显示具体数值
- 主题：跟随 Semi UI 色系（`var(--semi-color-primary)`）

#### 环形图：审计操作模块分布

- 数据：IAM / ARCHIVE / AI / SYSTEM 各模块操作占比
- 中心文字：总操作次数
- 图例：右侧竖排

#### 基础设施健康看板（仅超管）

- 每行：图标 + 组件名 + 状态点（绿/红）+ 延迟 ms + 详细信息
- 30 秒自动刷新
- 整个区块在非超管账号下完全不渲染（`v-if="userStore.isSuperAdmin"`）

#### 近期操作日志

- 复用现有 `GET /v1/audits?limit=10` 接口
- 显示：时间 + 用户名 + 操作描述（`action` + `module`）+ 状态点

---

### 7.6 文件清单（Dashboard 专属）

#### 新建文件
```
backend/app/api/v1/stats.py                       # 扩展现有统计 API + 新增 3 个端点
frontend/admin-web/pages/admin/index.vue           # 完全重写
frontend/admin-web/components/admin/dashboard/
  ├── KpiCard.vue                                  # 可复用 KPI 卡片（带趋势箭头）
  ├── UserActivityChart.vue                        # 折线图组件（ECharts）
  ├── AuditDistributionChart.vue                   # 环形图组件（ECharts）
  ├── InfraHealthPanel.vue                         # 基础设施健康看板（仅超管）
  └── RecentAuditFeed.vue                          # 近期审计日志列表
```

#### 修改文件
```
backend/app/api/v1/stats.py                       # 扩展 DashboardStats + 新接口
frontend/admin-web/api/iam.ts                     # 补充 StatsAPI 调用方法
```

---

### 7.7 待讨论点

1. **RabbitMQ Management API 端口**：默认 15672，docker-compose 是否已暴露？健康检查走内网还是直连？
2. **用户趋势数据源**：当前 audit_log 中 `action` 字段值是否已有 `USER_LOGIN` 这类标准值？还是需要先确认登录时写入了审计日志？
3. **非超管 Dashboard**：admin 角色进入 /admin 首页，基础设施看板隐藏后内容是否够用？是否需要加"本租户用户增长趋势"等补充内容？
4. **ECharts 主题**：跟随 Semi UI 的亮/暗模式自动切换，还是固定浅色主题？

---

## 八、文件清单

### 新建文件
```
backend/app/scripts/seed.py
frontend/admin-web/components/admin/PageHeader.vue
frontend/admin-web/components/admin/TenantSelector.vue
frontend/admin-web/components/admin/StatusBadge.vue
frontend/admin-web/stores/admin.ts               # 当前租户 context
```

### 修改文件
```
backend/app/bootstrap/lifespan.py                # 接入 seed
backend/.env                                     # 新增 ADMIN_PASSWORD / SKIP_SEED
frontend/admin-web/pages/admin/users/index.vue   # 重设计
frontend/admin-web/pages/admin/roles/index.vue   # 重设计
frontend/admin-web/pages/admin/organizations/index.vue  # 重设计
frontend/admin-web/pages/admin/tenants/index.vue # 重设计
frontend/admin-web/pages/admin/menus/index.vue   # 重设计
frontend/admin-web/components/layout/SystemHeader.vue   # 加租户选择器
```
