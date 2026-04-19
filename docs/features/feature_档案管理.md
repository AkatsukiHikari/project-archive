# 档案管理子系统设计文档

> **版本**: v1.0  
> **日期**: 2026-04-19  
> **状态**: 设计确认 · 待实现  
> **标准依据**: DA/T 18、DA/T 22、DA/T 42、GB/T 9705

---

## 一、业务背景与范围

档案管理子系统是 SAMS 的核心业务模块，覆盖档案的**收集、整理、归档、存储、检索**全链路。系统需同时满足：

- 中国档案行业标准（DA/T）的层级与字段规范
- 不同机构（馆/室）之间档案门类差异化的灵活性需求
- 业务人员批量导入为主的实际操作场景
- 高并发全文检索能力（Elasticsearch 加速层）

---

## 二、档案层级模型

### 2.1 DA/T 标准层级

```
全宗 (Fonds)
  └── 目录 (Catalog)          ← 档号编号域，现有模型缺失的关键层
        ├── [一文一件] 件 (Item)
        └── [案卷卷内] 案卷 (Volume)
                  └── 卷内文件 (Item)
```

### 2.2 整理方式

| 整理方式 | 层级结构 | 适用门类 |
|------|------|------|
| 一文一件 | 全宗 → 目录 → 件 | 文书、会计、照片、声像、电子、实物、大部分专业档案 |
| 案卷卷内 | 全宗 → 目录 → 案卷 → 卷内文件 | 科技档案、部分文书档案 |

---

## 三、档案门类体系

### 3.1 内置 DA/T 标准门类（`is_builtin=true`，不可删除）

| code | 名称 | 默认整理方式 |
|------|------|------|
| WS | 文书档案 | 一文一件 / 案卷卷内均支持 |
| KJ | 科技档案 | 案卷卷内为主 |
| HJ | 会计档案 | 一文一件 |
| ZP | 照片档案 | 一文一件 |
| SX | 声像档案 | 一文一件 |
| DZ | 电子档案 | 一文一件 |
| SW | 实物档案 | 一文一件 |

### 3.2 内置专业档案子门类（`is_builtin=true`，父类 code: `ZY`）

| code | 名称 | 核心专有字段 | 隐私保护 |
|------|------|------|------|
| ZY_HY | 婚姻档案 | 当事人姓名、证件号、婚姻状态、登记日期、登记机关 | 是 |
| ZY_FP | 扶贫档案 | 户主姓名、证件号、致贫原因、帮扶措施、退出时间 | 是 |
| ZY_TQ | 土地确权档案 | 权利人、证件号、地块编号、四至范围、面积、发证日期 | 是 |
| ZY_SC | 出生医疗证明 | 新生儿姓名、出生日期、母亲信息、接生机构、证件编号 | 是 |
| ZY_TY | 退役军人档案 | 姓名、证件号、服役年限、部队番号、退役类型 | 是 |
| ZY_DB | 低保档案 | 户主信息、家庭人口、低保类别、审批机关、起止日期 | 是 |

> 专业档案字段涉及个人隐私，`requires_privacy_guard=true`，读取权限单独控制，ES 中存脱敏版本。

### 3.3 自定义门类

业务人员可**克隆任意内置门类**后，通过**可视化表单设计器**增删字段，发布为本机构自定义门类。

---

## 四、数据库设计

### 4.1 表结构总览

```
repo_fonds                   全宗（保留，小改）
repo_archive_category        门类定义（含字段 schema）
repo_catalog                 目录（编号域）
repo_archive                 档案主表（统一件/案卷，JSON 混合）
repo_archive_no_rule         档号规则配置
repo_import_task             导入任务
repo_field_mapping_template  字段映射模板
```

### 4.2 `repo_archive_category`（门类定义表）

```sql
id              UUID PK
code            VARCHAR(20) UNIQUE          -- 门类代码
name            VARCHAR(100)                -- 门类名称
parent_id       UUID FK → self              -- 专业档案子门类的父类
base_category_id UUID FK → self            -- 克隆来源（自定义门类）
is_builtin      BOOLEAN DEFAULT false
requires_privacy_guard BOOLEAN DEFAULT false
field_schema    JSONB                       -- 字段定义列表（见 4.6）
archive_no_rule_id UUID FK → repo_archive_no_rule
tenant_id       UUID FK → iam_tenant
create_time, update_time, is_deleted        -- AuditMixin
```

### 4.3 `repo_catalog`（目录）

```sql
id              UUID PK
fonds_id        UUID FK → repo_fonds
category_id     UUID FK → repo_archive_category
catalog_no      VARCHAR(50)                 -- 目录号，同全宗内唯一
name            VARCHAR(255)
year            INTEGER                     -- 年度
org_mode        VARCHAR(20)                 -- by_item | by_volume
tenant_id       UUID FK → iam_tenant
-- AuditMixin
```

### 4.4 `repo_archive`（档案主表）

```sql
id              UUID PK
fonds_id        UUID FK → repo_fonds
catalog_id      UUID FK → repo_catalog
parent_id       UUID FK → self              -- NULL=顶级，有值=卷内文件
category_id     UUID FK → repo_archive_category
level           VARCHAR(10)                 -- volume | item

-- DA/T 必有项（规范化列，全部建索引）
archive_no      VARCHAR(100) INDEX          -- 档号（生成结果，可手动覆盖）
fonds_code      VARCHAR(50)  INDEX          -- 全宗号
catalog_no      VARCHAR(50)                 -- 目录号
volume_no       VARCHAR(50)                 -- 案卷号（一文一件时为空）
item_no         VARCHAR(50)                 -- 件号
year            INTEGER      INDEX          -- 年度
title           VARCHAR(512) INDEX          -- 题名
creator         VARCHAR(200) INDEX          -- 责任者
security_level  VARCHAR(20)                 -- 密级：public/internal/confidential/secret
retention_period VARCHAR(20)                -- 保管期限：permanent/long/short
doc_date        DATE                        -- 文件日期
pages           INTEGER                     -- 页数
status          VARCHAR(20)                 -- active/restricted/destroyed

-- 门类私有字段
ext_fields      JSONB                       -- GIN 索引

-- 存储引用
storage_key     VARCHAR(1024)
storage_bucket  VARCHAR(255)
file_size       BIGINT
file_format     VARCHAR(50)
sha256_hash     VARCHAR(64)

-- 系统字段
embedding_status VARCHAR(20) DEFAULT 'pending'  -- ES 同步状态
es_synced_at    TIMESTAMP                   -- 最后成功同步 ES 的时间
tenant_id       UUID FK → iam_tenant
-- AuditMixin
```

**索引策略：**
- `archive_no`, `fonds_code`, `year`, `title`, `creator` → B-tree 索引
- `ext_fields` → GIN 索引（支持 JSONB 路径查询）
- `(fonds_id, catalog_id, year)` → 联合索引（最常用检索路径）

### 4.5 `repo_archive_no_rule`（档号规则）

```sql
id              UUID PK
category_id     UUID FK → repo_archive_category
name            VARCHAR(100)
rule_template   JSONB       -- 规则段定义（见第五章）
seq_scope       VARCHAR(20) -- catalog | catalog_year | fonds
is_active       BOOLEAN DEFAULT true
tenant_id       UUID FK → iam_tenant
-- AuditMixin
```

### 4.6 `repo_import_task`（导入任务）

```sql
id              UUID PK
category_id     UUID FK → repo_archive_category
fonds_id        UUID FK → repo_fonds
catalog_id      UUID FK → repo_catalog
operator_id     UUID FK → iam_user
status          VARCHAR(20)  -- pending/running/done/failed
file_key        VARCHAR(1024)           -- 上传原始文件的存储键
mapping_snapshot JSONB                  -- 本次导入使用的映射快照
total           INTEGER DEFAULT 0
success         INTEGER DEFAULT 0
failed          INTEGER DEFAULT 0
skipped         INTEGER DEFAULT 0
error_report_key VARCHAR(1024)          -- 报表文件存储键
started_at      TIMESTAMP
finished_at     TIMESTAMP
tenant_id       UUID FK → iam_tenant
-- AuditMixin
```

### 4.7 `repo_field_mapping_template`（映射模板）

```sql
id              UUID PK
category_id     UUID FK → repo_archive_category
name            VARCHAR(100)
mappings        JSONB   -- [{source_col: "文件题名", target_field: "title"}, ...]
is_default      BOOLEAN DEFAULT false
tenant_id       UUID FK → iam_tenant
-- AuditMixin
```

---

## 五、档号规则引擎

### 5.1 规则段类型

`rule_template` 示例（文书档案一文一件，生成结果：`J001-2024-WS-0023`）：

```jsonc
{
  "separator": "-",
  "segments": [
    { "type": "field",    "field": "fonds_code" },
    { "type": "field",    "field": "year" },
    { "type": "literal",  "value": "WS" },
    { "type": "sequence", "padding": 4, "scope": "catalog_year" }
  ]
}
```

| 段类型 | 说明 |
|------|------|
| `field` | 取档案规范化字段值（fonds_code/year/catalog_no 等）|
| `literal` | 固定字符串 |
| `sequence` | 自增序号，scope 可选 `catalog`/`catalog_year`/`fonds` |
| `date_part` | 取日期字段的年/月/日部分（format 参数控制格式）|

### 5.2 序号并发安全

批量导入时使用 PostgreSQL `SELECT ... FOR UPDATE` 锁住当前 scope 下的最大序号，在事务内原子递增，避免并发重号。

### 5.3 管理入口

`/admin/archive/no-rules`：可视化配置规则段，实时预览生成结果。业务员可在档案详情页手动覆盖档号，覆盖操作写审计日志。

---

## 六、批量导入流程

### 6.1 五步流程

```
① 上传文件
   支持 CSV / XLSX / ODS 格式
   后端解析表头列表 → 返回前端
   文件暂存对象存储，创建 import_task(status=pending)

② 字段映射
   系统用已有映射模板做自动匹配（编辑距离/字符串相似度）
   前端展示：左=文件列头，右=门类字段下拉
   用户确认后可另存为新映射模板
   映射快照写入 import_task.mapping_snapshot

③ 预检（dry-run，不写库）
   扫描全部数据行：必填项校验、类型校验、档号冲突检测
   返回预检报告：成功 N 行 / 警告 N 行 / 失败 N 行及原因
   用户决定是否继续执行

④ 异步导入执行（Celery Task）
   500 条/批写入 repo_archive
   每批完成后：
     - 更新 import_task.success/failed 计数
     - bulk index 同批数据到 Elasticsearch
     - WebSocket 推送进度到前端
   失败行记录错误原因，不阻塞后续批次

⑤ 完成 & 报表
   生成 XLSX 报表：成功明细 + 失败明细（含失败原因列）
   报表存对象存储，前端提供下载
   import_task.status = done / failed
```

### 6.2 前端进度看板

```
导入任务 #2024-001                        [运行中]
█████████████████░░░░░░░  68%
成功 682   失败 12   剩余 318   总计 1012
[查看失败明细]   [后台运行，关闭窗口不影响]
```

---

## 七、Elasticsearch 同步设计

### 7.1 同步策略

| 场景 | 同步方式 |
|------|------|
| 单条创建/更新 | API 写 PG 事务提交后 → 发 Celery 异步任务 → ES index/update |
| 单条软删除 | 同步 ES delete |
| 批量导入 | 每 500 条/批写完 PG → 同批 bulk index 到 ES |
| 管理员全量重建 | 后台 Celery 任务分页扫描 PG → 全量 bulk index |

### 7.2 ES 索引 Mapping

```jsonc
{
  "mappings": {
    "properties": {
      "archive_no":       { "type": "keyword" },
      "fonds_code":       { "type": "keyword" },
      "year":             { "type": "integer" },
      "title":            { "type": "text", "analyzer": "ik_max_word" },
      "creator":          { "type": "text", "analyzer": "ik_max_word" },
      "security_level":   { "type": "keyword" },
      "retention_period": { "type": "keyword" },
      "category_code":    { "type": "keyword" },
      "doc_date":         { "type": "date" },
      "ext_fields":       { "type": "object", "dynamic": true },
      "tenant_id":        { "type": "keyword" }
    }
  }
}
```

- 中文字段使用 `ik_max_word` 分词器（需安装 elasticsearch-analysis-ik 插件）
- 专业档案隐私字段（证件号等）在 ES 中存脱敏版本（前 3 位 + `***`）
- `ext_fields` 动态 mapping，按门类 `field_schema` 预置 mapping 模板

### 7.3 同步失败处理

- ES 不可用时**不影响 PG 写入**（ES 是查询加速层，PG 是主存储）
- 失败任务进 Celery retry 队列，指数退避重试最多 3 次
- 仍失败则写 `sync_error` 日志，标记 `repo_archive.es_synced_at=NULL`
- 管理员可在后台触发**全量重建索引**，修复所有未同步数据

---

## 八、可视化表单设计器

### 8.1 字段 Schema 结构

`repo_archive_category.field_schema` 字段定义数组：

```jsonc
[
  {
    "name": "project_code",
    "label": "项目编号",
    "type": "text",           // text | number | date | select | boolean | textarea
    "required": true,
    "placeholder": "请输入项目编号",
    "validation": { "maxLength": 50, "pattern": "^[A-Z0-9-]+$" },
    "options": null,          // type=select 时填枚举值数组
    "inherited": false        // true=从父门类继承，不可删除
  },
  {
    "name": "drawing_type",
    "label": "图纸类别",
    "type": "select",
    "required": false,
    "options": ["施工图", "竣工图", "草图"],
    "inherited": false
  }
]
```

### 8.2 设计器功能

- 从基础门类克隆后进入设计器，继承字段标记为锁定（不可删除，可改 label）
- 支持：添加字段、拖拽排序、设置类型/必填/校验规则/枚举选项
- 实时预览表单渲染效果
- 保存后可选择发布或保存草稿

---

## 九、API 结构

```
/api/v1/archive/
  categories/                    门类 CRUD + 克隆
  categories/{id}/schema         字段 schema 读写（设计器）
  categories/{id}/publish        发布门类

  no-rules/                      档号规则 CRUD
  no-rules/{id}/preview          预览生成档号

  fonds/                         全宗 CRUD
  catalogs/                      目录 CRUD
  records/                       档案主表 CRUD + 列表检索
  records/{id}/override-no       手动覆盖档号（记审计日志）

  import/upload                  上传文件 → 返回列头
  import/preview                 字段映射 + dry-run 预检
  import/execute                 启动异步导入
  import/tasks/{id}              任务进度查询
  import/tasks/{id}/report       下载导入报表
  mapping-templates/             映射模板 CRUD

/ws/import/{task_id}             WebSocket 实时进度推送
```

---

## 十、模块目录结构

```
backend/app/modules/
  repository/                    (现有，重构)
    models/
      archive.py                 repo_archive + repo_catalog
      category.py                repo_archive_category
      no_rule.py                 repo_archive_no_rule
    services/
      archive_service.py
      category_service.py
      no_rule_engine.py          档号规则引擎
      es_sync_service.py         ES 同步服务
    repositories/
      archive_repo.py
      category_repo.py
    api/
      routes_archive.py
      routes_category.py
      routes_no_rule.py

  collection/                    (现有，扩展)
    models/
      import_task.py             repo_import_task
      mapping_template.py        repo_field_mapping_template
    services/
      import_service.py          五步导入流程
      mapping_service.py         自动列头映射
    tasks/
      import_task.py             Celery 异步导入任务
      es_rebuild_task.py         全量重建 ES 索引
    api/
      routes_import.py
```

---

## 十一、待确认事项

- [ ] ES 版本（7.x / 8.x）及 ik 分词器已部署确认
- [ ] 专业档案隐私字段脱敏规则细化（证件号/手机号各自规则）
- [ ] 档案销毁流程是否纳入本期范围（`status=destroyed` 后的处置审批）
- [ ] 全量重建 ES 索引的触发权限（超级管理员 / 档案管理员）
