---
title: SAMS AI 客户推介 PDF 设计稿
date: 2026-05-18
status: approved (方案 A)
audience: 客户决策层 + 客户技术对接(混合)
positioning: AI 占 ≥70% 篇幅,通用产品推介,非客户定制
delivery: HTML(深色科技感) → Chrome headless → PDF
---

# SAMS AI 客户推介 PDF 设计稿

## 0. 目的

让一份 PDF 同时承担两件事:
- **领导翻 5 页**就明白 SAMS 的 AI 能解决什么、为什么靠谱、什么时候能落地
- **技术翻完全程**就能评估架构、安全合规、对接成本

## 1. 交付物

- HTML 源文件:`docs/marketing/sams-ai-pitch/index.html`(单文件,Tailwind via CDN)
- 资源:`docs/marketing/sams-ai-pitch/assets/`(图标/示意图 SVG)
- 构建脚本:`docs/marketing/sams-ai-pitch/build.sh`(调用 Chrome headless 产出 PDF)
- 成品:`docs/marketing/sams-ai-pitch/SAMS-AI-Pitch.pdf`

## 2. 章节结构(方案 A,28-32 页)

| # | 章节 | 页数 | 受众 | 内容 |
|---|---|---|---|---|
| 1 | 封面 | 1 | 全 | SAMS 标识 + 一句话价值主张 + 版本日期 |
| 2 | 致客户:三个真问题 | 1 | 领导 | 档案数字化的痛点钩子(海量入库慢/检索难/利用价值低) |
| 3 | SAMS 一图全景 | 2 | 全 | 6 大模块鸟瞰(采集/保管/利用/四性…),AI 高亮 |
| 4 | AI 能改变什么 | 2 | 领导 | 9 大场景一览表 + 业务价值速览 |
| 5-13 | **AI 能力九讲** | 14 | 全 | 每能力 1.5 页:场景图 / 真实效果 / 界面示意 / 用户旁白 |
| 14 | γ 架构:Dify + Gateway | 1 | 技术 | 分层图 + 五条不可破坏约束 |
| 15 | HITL 三档闸门 | 1 | 技术 | auto/review/manual + 审核队列流程 |
| 16 | 不胡说:引用强制 + 拒答 | 1 | 全 | citation 校验 / 越权拦截 |
| 17 | Eval 黄金集门禁 | 1 | 技术 | 黄金集 → 阈值 → 灰度 → 回滚 |
| 18 | 权限/密级/租户隔离 | 1 | 技术 | RBAC + 引用越权防御表 |
| 19 | 落地路线图 P1→P4 | 2 | 全 | 时间轴 + 各期里程碑 |
| 20 | 与既有系统对接 | 1 | 技术 | DA/T 合规 / SSO / 国密 / 审计 |
| 21 | 附录 | 2 | 技术 | 错误码 6000 段 / 模型档位 / 关键配置 |
| 22 | 联系页 | 1 | 全 | 商务对接信息(留占位) |

九讲顺序按"价值递增 + 风险递增"(沿用既有 AI Agent 设计 §2):
1. RAG 智能问答 🟢
2. 自然语言检索 🟢
3. 知识库交互管理 🟢
4. 档案自动挂接 🟡
5. AI 自动编目 🟡
6. 档案摘要/综述 🟡
7. 四性检测辅助 🔴(建议态)
8. 审稿/拟稿 🔴(建议态)
9. 跨档案关联分析 🔴(建议态)

每讲页面模板固定 4 块:
- **左上**:能力名 + 难度色标 + "完整/建议态"形态徽章
- **右上**:一句话价值
- **中部**:界面示意图(SVG 占位) + 数据/效果指标
- **底部**:用户旁白引用(模拟客户场景台词)

## 3. 视觉规范

呼应既有 `/ai` 页"AI 的地盘"约定:

- **基色**:深背景 `#0A0E1A`(近黑藏蓝),主色青蓝紫渐变 `from-cyan-400 via-violet-500 to-fuchsia-500`
- **质感**:玻璃拟态卡片(`backdrop-blur-xl` + 半透明白边)、内发光、subtle 噪点纹理
- **字体**:标题 Inter 800/紧 tracking,正文系统字体栈 + 中文 PingFang/微软雅黑回退
- **色标**:🟢 `emerald-400` / 🟡 `amber-400` / 🔴 `rose-400`(能力难度统一标识)
- **页眉页脚**:页眉左上 SAMS · AI 推介,右上 章节名;页脚右下页码 N/M
- **页面尺寸**:A4 竖版 (210×297mm),适合文档传阅与邮件分发
- **打印安全区**:四周 16mm padding,所有内容必须落在打印区内

## 4. 工具链与构建

```bash
# 构建命令(写入 build.sh)
/Applications/Google\ Chrome.app/Contents/MacOS/Google\ Chrome \
  --headless --disable-gpu --no-pdf-header-footer \
  --print-to-pdf=SAMS-AI-Pitch.pdf \
  --print-to-pdf-no-header \
  file://$(pwd)/index.html
```

- HTML 单文件 + 内联 SVG,Tailwind 用 CDN 版本(打印前需触发 CSS 生成)
- 用 `@media print` 控制分页 `page-break-after: always`
- 每个"页"在 HTML 中是一个 `<section class="page">`,统一 A4 物理尺寸

## 5. 内容来源

九讲页内容指标直接引用 `docs/superpowers/specs/2026-05-11-archive-ai-agent-design.md` §2 能力清单。架构图/HITL/Eval/路线图同源该 spec §3-7。无需新增设计判断,只做"技术语言 → 客户语言"翻译。

## 6. 不做的事

- 不引入额外构建依赖(no puppeteer/playwright npm install)
- 不为这份 PDF 改前端项目代码
- 不放真实截图(P1 都没全实装,放截图反而风险);全部用 SVG 示意图
- 不放具体客户名/案例数据(本期是通用材料)
- 不出英文版

## 7. 验收标准

- PDF 28-32 页,A4 竖版
- 在 macOS Preview + Adobe Reader 打开都不破版
- 每页内容在 16mm 安全区内
- 文件大小 < 8MB
- Hikari 翻一遍认为"现场能讲、邮件能发"

---

**评审状态**:用户已批准方案 A 章节结构,本稿落档后直接进入实施(per 项目惯例 feedback_workflow_no_plans:不写 plan 文件,设计稿确认即开工)。
