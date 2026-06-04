"""
L4 业务规则知识库种子（30 条 DA/T 标准 + 内部规章）

设计稿 §4.1：P1 交付 L1 元数据 + L4 业务规则手动导入。
L4 内容以"全租户共享 + 静态版本号"形式存入 ES sams_ai_rules 索引。

运行::

    cd backend && uv run python -m app.scripts.seed_ai_rules
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone

from app.infra.search.es_client import (
    AI_RULES_INDEX,
    AI_RULES_INDEX_MAPPING,
    SHARED_TENANT_ID,
    get_es_client,
)

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# 30 条业务规则种子 ───────────────────────────────────────────────────────
# 字段说明：
# - rule_id   全局唯一稳定 ID（命名约定：domain.subkey）
# - category  归类：retention / secret_level / archive_no / four_natures / lifecycle / metadata
# - source    出处：DA/T 编号 / GB/T 编号 / 内部规章
# - version   规则文档版本，规则升级时手动改
RULES: list[dict] = [
    # ── 保管期限 (retention) ─────────────────────────────────────────
    {
        "rule_id": "retention.permanent",
        "category": "retention",
        "title": "永久保管期限定义",
        "content": "永久保管的档案是指对国家、社会、本机关具有长远利用价值的档案，应当长期完整保存，不得销毁。包括重要决策、组织机构变迁、人事任免、土地房产权属等。",
        "tags": ["BGQX", "永久", "保管期限"],
        "version": "v2024.01",
        "source": "DA/T 15-2023",
        "secret_level": 0,
    },
    {
        "rule_id": "retention.long",
        "category": "retention",
        "title": "长期保管期限定义",
        "content": "长期保管的档案是指在较长时间内对本机关、本系统有查考利用价值的档案，保管期限一般为 30 年。如普通业务往来文件、规范性技术资料等。",
        "tags": ["BGQX", "长期", "30年"],
        "version": "v2024.01",
        "source": "DA/T 15-2023",
        "secret_level": 0,
    },
    {
        "rule_id": "retention.short",
        "category": "retention",
        "title": "短期保管期限定义",
        "content": "短期保管的档案是指在较短时间内对本机关有查考利用价值的档案，保管期限一般为 10 年。期满后由档案部门组织鉴定，确无保存价值的依法销毁。",
        "tags": ["BGQX", "短期", "10年"],
        "version": "v2024.01",
        "source": "DA/T 15-2023",
        "secret_level": 0,
    },
    {
        "rule_id": "retention.review",
        "category": "retention",
        "title": "保管期限到期复查",
        "content": "短期、长期保管期限到期前 6 个月，档案管理系统自动进入'期限复查'队列。复查后可延长保管期限或转入销毁审批流程。",
        "tags": ["BGQX", "复查", "鉴定"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },

    # ── 密级 (secret_level) ──────────────────────────────────────────
    {
        "rule_id": "secret.levels",
        "category": "secret_level",
        "title": "档案密级分类",
        "content": "档案密级从低到高分为五级：公开（public/公开）、内部（internal/内部）、秘密（secret/秘密）、机密（confidential/机密）、绝密（top_secret/绝密）。MJ 字段必须填充这五类之一。",
        "tags": ["MJ", "密级", "公开", "秘密", "机密", "绝密"],
        "version": "v2024.01",
        "source": "GB/T 7156-2003",
        "secret_level": 0,
    },
    {
        "rule_id": "secret.access_rule",
        "category": "secret_level",
        "title": "密级访问控制原则",
        "content": "用户只能访问不高于其个人密级的档案。AI 检索代理在查询时按用户密级自动构造 MJ 允许列表，越权引用会被引用校验器拦截，整段答案替换为'出处校验失败'。",
        "tags": ["MJ", "访问控制", "RBAC"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "secret.top_secret_handling",
        "category": "secret_level",
        "title": "绝密档案处理要求",
        "content": "绝密档案不得通过 AI 通道导出全文；AI 摘要场景遇到绝密档案直接拒答，不在引用列表中暴露其存在。绝密档案的利用必须走线下专门审批。",
        "tags": ["绝密", "top_secret", "拒答"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "secret.declassification",
        "category": "secret_level",
        "title": "档案解密规则",
        "content": "秘密级一般保密期不超过 10 年，机密级不超过 20 年，绝密级不超过 30 年。到期后由保密委员会评审，决定解密、降密或延期。",
        "tags": ["解密", "降密", "保密期"],
        "version": "v2024.01",
        "source": "GB/T 7156-2003",
        "secret_level": 0,
    },

    # ── 档号规则 (archive_no) ────────────────────────────────────────
    {
        "rule_id": "archive_no.structure",
        "category": "archive_no",
        "title": "档号 DH 字段结构",
        "content": "档号（DH）由全宗号（QZH）-门类代码-年度（ND）-保管期限（BGQX）-顺序号组成。示例：A001-WS-2024-Y-00001 表示 A001 全宗 2024 年度文书永久档第 1 件。",
        "tags": ["DH", "档号", "结构"],
        "version": "v2024.01",
        "source": "DA/T 13-2022",
        "secret_level": 0,
    },
    {
        "rule_id": "archive_no.fonds",
        "category": "archive_no",
        "title": "全宗号 QZH 命名",
        "content": "全宗号（QZH）由档案馆按机关代码统一分配，一般为 3-5 位字母数字组合。同一全宗在系统中的 QZH 终身不变；机关合并/拆分时按归档规则继承或新增。",
        "tags": ["QZH", "全宗号"],
        "version": "v2024.01",
        "source": "DA/T 13-2022",
        "secret_level": 0,
    },
    {
        "rule_id": "archive_no.sequence",
        "category": "archive_no",
        "title": "顺序号生成与并发",
        "content": "顺序号按 (全宗号, 年度, 门类) 维度独立递增，由 ArchiveNoSeq 表的 current_seq 字段维护。并发请求通过行锁保证不重号。",
        "tags": ["顺序号", "并发", "NoRule"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "archive_no.rule_segments",
        "category": "archive_no",
        "title": "档号规则引擎可用段类型",
        "content": "档号规则引擎支持四类段：field（直接字段值，如 QZH、ND）、literal（字面量分隔符，如 - 或 .）、sequence（顺序号，可定宽补零）、date_part（年度的子部分，如 YYYY/YY）。",
        "tags": ["NoRule", "段类型"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },

    # ── 四性 (four_natures) ──────────────────────────────────────────
    {
        "rule_id": "four_natures.definition",
        "category": "four_natures",
        "title": "电子档案四性要求",
        "content": "电子档案必须满足四性：真实性（authenticity，来源可追溯）、完整性（integrity，内容无篡改）、可用性（usability，可读可解析）、安全性（security，符合密级要求）。归档前必须通过四性检测。",
        "tags": ["四性", "真实性", "完整性", "可用性", "安全性"],
        "version": "v2024.01",
        "source": "GB/T 39362-2020",
        "secret_level": 0,
    },
    {
        "rule_id": "four_natures.authenticity",
        "category": "four_natures",
        "title": "真实性检测要点",
        "content": "真实性检测：核对来源系统、生成时间、责任者签名/电子印章；元数据元素必须包含归档机构、形成时间、原始格式。AI 仅做风险提示，不下判定结论。",
        "tags": ["真实性", "authenticity"],
        "version": "v2024.01",
        "source": "GB/T 39362-2020",
        "secret_level": 0,
    },
    {
        "rule_id": "four_natures.integrity",
        "category": "four_natures",
        "title": "完整性检测要点",
        "content": "完整性检测：通过哈希值（SHA-256）校验比对入库前后文件是否变化；多文件档案需校验子文件清单完整。AI 检测到哈希不一致直接标红，不允许 auto 落库。",
        "tags": ["完整性", "integrity", "哈希"],
        "version": "v2024.01",
        "source": "GB/T 39362-2020",
        "secret_level": 0,
    },
    {
        "rule_id": "four_natures.usability",
        "category": "four_natures",
        "title": "可用性检测要点",
        "content": "可用性检测：文件能用预定的软件正常打开、内容可读、版式正确。建议归档格式：PDF/A、TIFF、XML、文本类 UTF-8 编码。专有格式归档前必须转换。",
        "tags": ["可用性", "usability", "格式"],
        "version": "v2024.01",
        "source": "GB/T 39362-2020",
        "secret_level": 0,
    },
    {
        "rule_id": "four_natures.security",
        "category": "four_natures",
        "title": "安全性检测要点",
        "content": "安全性检测：访问权限标记正确（MJ 字段、利用范围）、加密措施得当（绝密档案必须加密存储）、备份策略合规。检测不通过的档案不能进入正式库。",
        "tags": ["安全性", "security"],
        "version": "v2024.01",
        "source": "GB/T 39362-2020",
        "secret_level": 0,
    },

    # ── 生命周期 (lifecycle) ─────────────────────────────────────────
    {
        "rule_id": "lifecycle.transfer",
        "category": "lifecycle",
        "title": "归档移交流程",
        "content": "形成单位在文件办毕后次年的 1-3 月内向档案部门移交。移交清单经双方核对后签字，纸质件入库上架，电子件落 staging 表等待编目。",
        "tags": ["移交", "归档", "transfer"],
        "version": "v2024.01",
        "source": "DA/T 32-2018",
        "secret_level": 0,
    },
    {
        "rule_id": "lifecycle.staging_to_archived",
        "category": "lifecycle",
        "title": "临时库到正式库的状态机",
        "content": "档案先入 repo_archive_staging 表（draft → pending_review → archived/rejected）。通过审核的转入 repo_archive 正式库（archived → active → restricted → pending_destroy → destroyed）。",
        "tags": ["状态机", "staging", "archived"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "lifecycle.destruction",
        "category": "lifecycle",
        "title": "档案销毁审批流程",
        "content": "短期档案到期后经鉴定确无价值的进入销毁队列，需经档案部门负责人 + 形成单位负责人 + 监察部门三方会签。销毁过程必须留全程录像或两人以上现场签字，销毁清单永久保存。",
        "tags": ["销毁", "destruction", "审批"],
        "version": "v2024.01",
        "source": "DA/T 32-2018",
        "secret_level": 0,
    },
    {
        "rule_id": "lifecycle.utilization",
        "category": "lifecycle",
        "title": "档案利用申请",
        "content": "利用方式：查阅、借阅、复制、出具证明。借阅期限通常不超过 10 个工作日，到期未还自动告警。涉密档案利用前必须核对申请人密级许可。",
        "tags": ["利用", "借阅", "复制"],
        "version": "v2024.01",
        "source": "DA/T 32-2018",
        "secret_level": 0,
    },

    # ── 元数据 (metadata) ───────────────────────────────────────────
    {
        "rule_id": "metadata.required_fields",
        "category": "metadata",
        "title": "档案核心元数据必填字段",
        "content": "必填：QZH（全宗号）、TM（题名）、ND（年度）、MJ（密级）、BGQX（保管期限）。条件必填：DH（档号，由规则引擎生成或手工填写）、RZZ（责任者，人事/财务类强制）。",
        "tags": ["元数据", "必填", "TM", "ND", "QZH"],
        "version": "v2024.01",
        "source": "DA/T 18-2022",
        "secret_level": 0,
    },
    {
        "rule_id": "metadata.field_naming",
        "category": "metadata",
        "title": "档案字段拼音缩写命名约定",
        "content": "本系统档案核心字段统一使用拼音首字母缩写：DH=档号、QZH=全宗号、TM=题名、ND=年度、MJ=密级、BGQX=保管期限、WJRQ=文件日期、RZZ=责任者、YS=页数。AI patch 字段名必须遵守此规范。",
        "tags": ["命名", "拼音", "字段"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "metadata.catalog_types",
        "category": "metadata",
        "title": "目录类型 catalog_type",
        "content": "案卷目录（juan_mu）：传统案卷形态，一卷多件；卷内目录（juan_nei）：案卷内的件级目录；一文一件（yi_wen_yi_jian）：直接管理到件，没有卷的概念，主流电子档案使用。",
        "tags": ["catalog_type", "案卷", "卷内", "一文一件"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "metadata.attachment",
        "category": "metadata",
        "title": "档案附件管理",
        "content": "原文附件存储在 repo_archive_attachment 表，与档案主体一对多关系。附件需记录文件格式、大小、哈希值、存储路径。删除档案时附件级联软删除，物理文件保留待 GC。",
        "tags": ["附件", "attachment", "原文"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },

    # ── AI 系统使用约定 (ai_usage) ─────────────────────────────────
    {
        "rule_id": "ai_usage.write_via_patch",
        "category": "ai_usage",
        "title": "AI 写操作必须走 patch",
        "content": "AI 不直接 INSERT/UPDATE 档案表，所有写操作产出 staging patch，按 HITL 闸门档位（auto/review/manual）处理。这是不可破坏的设计约束。",
        "tags": ["patch", "HITL", "写操作"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "ai_usage.citation_required",
        "category": "ai_usage",
        "title": "AI 输出必须带引用",
        "content": "问答 / 摘要 / 检索三类输出必须附 citations[] 列表。无证据则拒答。前端无引用 chip 的答案置灰并标'未引证'。",
        "tags": ["引用", "citation", "拒答"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "ai_usage.high_risk_capabilities",
        "category": "ai_usage",
        "title": "高风险能力的建议态形态",
        "content": "四性检测辅助、AI 拟稿、跨档案关联三类能力永远以'AI 建议卡片'形态出现，不自动落库。用户采纳时手动复制到正式表单或触发审批流。",
        "tags": ["建议态", "四性", "拟稿", "关联"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "ai_usage.model_tiers",
        "category": "ai_usage",
        "title": "模型档位选择指引",
        "content": "快档位（Qwen-Turbo/Haiku 级）适合简单问答、检索改写、轻量摘要；准档位（Qwen-Max/Sonnet 级，默认）适合编目抽取、四性建议、复杂综述；思考档位（DeepSeek-R1/Opus 级）适合跨档案关联、拟稿、需推理场景。",
        "tags": ["模型", "档位", "快", "准", "思考"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
    {
        "rule_id": "ai_usage.eval_threshold",
        "category": "ai_usage",
        "title": "AI 能力上线门禁",
        "content": "每个 AI 能力必须有黄金集 + 准确率阈值。Workflow 升版必须先过 Eval；驳回的 patch 自动进'待标注池'反哺黄金集。",
        "tags": ["Eval", "门禁", "黄金集"],
        "version": "v2024.01",
        "source": "内部规章",
        "secret_level": 0,
    },
]


async def main() -> None:
    client = get_es_client()

    # 索引存在性确保
    try:
        if not await client.indices.exists(index=AI_RULES_INDEX):
            await client.indices.create(index=AI_RULES_INDEX, body=AI_RULES_INDEX_MAPPING)
            logger.info("Elasticsearch 索引 '%s' 创建", AI_RULES_INDEX)
    except Exception as exc:
        logger.error("无法访问 Elasticsearch：%s", exc)
        return

    now = datetime.now(timezone.utc).isoformat()
    inserted = 0
    for rule in RULES:
        doc = {
            "rule_id": rule["rule_id"],
            "tenant_id": SHARED_TENANT_ID,
            "category": rule["category"],
            "title": rule["title"],
            "content": rule["content"],
            "tags": rule["tags"],
            "version": rule["version"],
            "source": rule["source"],
            "secret_level": rule["secret_level"],
            "create_time": now,
        }
        await client.index(index=AI_RULES_INDEX, id=rule["rule_id"], document=doc)
        inserted += 1

    # 等待索引刷新（让搜索可见）
    await client.indices.refresh(index=AI_RULES_INDEX)
    logger.info("L4 规则种子完成 ✓ 总数=%d", inserted)

    # 关闭客户端避免 unclosed 警告
    await client.close()


if __name__ == "__main__":
    asyncio.run(main())
