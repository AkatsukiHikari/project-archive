"""
Dify Chatflow / Workflow DSL 构造器

参考 Dify 1.13.3 源码 /app/api/dify_graph/enums.py 与 /app/api/tests/fixtures/workflow/。

设计稿 A' 方案：
  1 个主 Chatflow App（advanced-chat） + 8 个子 Workflow App（workflow）

主 Chatflow 结构：
    Start ─→ Question Classifier ─→ HTTP Request（回调后端 dispatch）─→ Answer

子 Workflow 结构：
    Start ─→ HTTP Request（回调后端 /v1/ai/internal/tool/dispatch）─→ LLM（格式化输出）─→ End
"""
from __future__ import annotations

import json
import uuid
from dataclasses import dataclass


OLLAMA_PLUGIN_IDENT = (
    "langgenius/ollama:0.1.3@"
    "66e156c4f612964c131c49168882e78c2cdfe366879506b97ad855b23c5d6d98"
)

# 后端在 docker 网络外，对 Dify 容器可访问的地址：
# - host.docker.internal:8000 （Linux/Mac docker-desktop）
# - 实际部署改成内网域名
BACKEND_URL_FROM_DIFY = "http://host.docker.internal:8000"

DIFY_DEPENDENCIES = [
    {
        "current_identifier": None,
        "type": "marketplace",
        "value": {
            "marketplace_plugin_unique_identifier": OLLAMA_PLUGIN_IDENT,
            "version": None,
        },
    }
]


@dataclass(frozen=True)
class ScenarioMeta:
    code: str
    name: str
    description: str
    icon: str
    icon_bg: str
    classifier_label: str        # 在主 Chatflow Classifier 节点里显示的类别名
    classifier_examples: list[str]  # 训练 classifier 的例句
    sub_workflow_prompt: str     # 子 Workflow LLM 节点的 system prompt


SCENARIOS: list[ScenarioMeta] = [
    ScenarioMeta(
        code="qa",
        name="档案智能问答",
        description="基于档案知识库的检索增强问答",
        icon="speech_balloon",
        icon_bg="#E0F2FE",
        classifier_label="问答",
        classifier_examples=[
            "永久保管期限是多久",
            "档号是如何组成的",
            "四性检测包含哪些",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 档案问答助手。\n"
            "基于 {{#http.body#}} 中的 citations 数据回答用户问题。\n"
            "无证据时回答：『未在知识库中找到相关档案或规则。』\n"
            "用专业、简洁的中文输出，每条信息标注出处。"
        ),
    ),
    ScenarioMeta(
        code="search",
        name="自然语言检索",
        description="自然语言查询转结构化检索，定位档案",
        icon="mag",
        icon_bg="#FEF3C7",
        classifier_label="检索",
        classifier_examples=[
            "查 2024 年的财务凭证",
            "找市档案馆人事任免文件",
            "数字化建设相关档案",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 自然语言检索助手。\n"
            "根据 {{#http.body#}} 的检索命中结果，向用户呈现：\n"
            "  ① 推断的检索意图\n"
            "  ② 命中档案列表（题名 · 档号 · 年度 · 全宗号）\n"
            "  ③ 若无命中，提示用户细化条件。"
        ),
    ),
    ScenarioMeta(
        code="summary",
        name="档案专题综述",
        description="按主题/全宗/类目生成专题综述",
        icon="memo",
        icon_bg="#FCE7F3",
        classifier_label="综述",
        classifier_examples=[
            "2024 年度财务工作综述",
            "近三年数字化建设进展",
            "永久保管档案管理要点",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 档案综述助手。\n"
            "基于 {{#http.body#}} 的档案数据，生成结构化综述：\n"
            "  一、概述\n"
            "  二、关键档案与规则（每条带出处）\n"
            "  三、结论与建议\n"
            "禁止编造，引用不足时明确指出缺口。"
        ),
    ),
    ScenarioMeta(
        code="attach",
        name="档案自动挂接",
        description="新材料匹配档案，产出挂接 patch",
        icon="link",
        icon_bg="#DCFCE7",
        classifier_label="挂接",
        classifier_examples=[
            "把这份新材料挂接到合适的目录",
            "为这份文件找归属档案",
            "新材料归类到哪个目录",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 档案自动挂接助手。\n"
            "{{#http.body#}} 包含候选档案匹配结果与生成的 patch_id。\n"
            "向用户呈现：推荐目标 · 匹配依据 · 置信度。\n"
            "提示用户：本能力产出 staging patch，需走人工审核。"
        ),
    ),
    ScenarioMeta(
        code="catalog",
        name="AI 自动编目",
        description="从档案文本抽取元数据生成编目 patch",
        icon="card_index_dividers",
        icon_bg="#E0E7FF",
        classifier_label="编目",
        classifier_examples=[
            "从这段文字抽取档案字段",
            "自动编目这份文件",
            "提取题名责任者年度",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 档案自动编目助手。\n"
            "{{#http.body#}} 给出了抽取结果。\n"
            "向用户呈现：抽取出的标准字段（TM/RZZ/ND/MJ/BGQX）\n"
            "+ 不确定字段标记 + 置信度。"
        ),
    ),
    ScenarioMeta(
        code="fournat",
        name="四性检测建议",
        description="真实性/完整性/可用性/安全性 风险提示",
        icon="shield",
        icon_bg="#FEE2E2",
        classifier_label="四性",
        classifier_examples=[
            "做四性检测",
            "档案的真实性如何评估",
            "归档前的可用性风险",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 四性检测辅助助手。\n"
            "基于 {{#http.body#}} 数据，从四维度给出风险提示：\n"
            "  ① 真实性 ② 完整性 ③ 可用性 ④ 安全性\n"
            "只提示风险，不下判定；用『可能 / 建议 / 需要核对』措辞。"
        ),
    ),
    ScenarioMeta(
        code="draft",
        name="拟稿助手",
        description="鉴定意见 / 销毁建议 / 利用报告草稿",
        icon="lower_left_fountain_pen",
        icon_bg="#DBEAFE",
        classifier_label="拟稿",
        classifier_examples=[
            "拟一份销毁建议",
            "写一份利用工作报告",
            "起草档案鉴定意见",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 档案拟稿助手。\n"
            "基于 {{#http.body#}} 数据生成正式公文草稿：\n"
            "  ① 标题（公文规范）② 正文（分条款、引用准确）③ 落款建议\n"
            "强调：草稿不替代正式签发。"
        ),
    ),
    ScenarioMeta(
        code="relate",
        name="跨档案关联",
        description="找语义/时间/责任者相关的其他档案",
        icon="link",
        icon_bg="#F3E8FF",
        classifier_label="关联",
        classifier_examples=[
            "找跟这份档案相关的其他档案",
            "档案的关联分析",
            "类似主题的档案有哪些",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 跨档案关联助手。\n"
            "基于 {{#http.body#}} 呈现关联建议：\n"
            "  ① 相关档案列表（题名 · 档号 · 关联理由）\n"
            "  ② 置信度（实体消歧可能歧义）\n"
            "  ③ 推荐进一步检索的关键词。"
        ),
    ),
    ScenarioMeta(
        code="kb_manage",
        name="知识库管理",
        description="查询索引状态、触发重建",
        icon="card_file_box",
        icon_bg="#FEF3C7",
        classifier_label="知识库",
        classifier_examples=[
            "知识库现在有多少档案",
            "如何重建索引",
            "L4 业务规则有哪些类别",
        ],
        sub_workflow_prompt=(
            "你是 SAMS 知识库管理助手。\n"
            "{{#http.body#}} 包含 L1 元数据 + L4 规则 + L2 OCR 三类 KB 的状态。\n"
            "向用户呈现：索引文档数 / 上次同步时间 / 重建提示。"
        ),
    ),
]


def _gen_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:8]}"


# ── 主 Chatflow 构造 ────────────────────────────────────────────────────────


def build_master_chatflow(service_token: str = "") -> dict:
    """主 Chatflow（真分发版）：Start → 意图分类(真接线) → 各意图独立分支 → Answer(流式)

    每个意图一条分支：分支内 HTTP 调对应后端 capability 取权威数据，再由该意图自己的
    LLM 节点按意图排版并逐 token 流式输出。慢但真：分类器真正参与执行、每意图逻辑独立。

    service_token: 配置 AI_SERVICE_TOKEN 时，给每条分支的 dispatch HTTP 加 X-Service-Token 头。
    """
    start_id = "node_start"
    classifier_id = "node_classifier"

    classifier_classes = [
        {"id": sc.code, "name": f"{sc.classifier_label}（{sc.description}）"}
        for sc in SCENARIOS
    ]
    examples_text = "\n".join(
        f"- 「{ex}」 → {sc.classifier_label}"
        for sc in SCENARIOS for ex in sc.classifier_examples
    )
    classifier_instruction = (
        "根据用户的提问内容，从以下档案业务场景中选择最匹配的一个：\n"
        + "\n".join(f"  {sc.classifier_label}: {sc.description}" for sc in SCENARIOS)
        + "\n\n参考示例：\n"
        + examples_text
        + "\n\n判断要点：含『查/找』→检索；『综述/汇总』→综述；『新材料/挂接』→挂接；"
        "『字段/抽取』→编目；『真实性/完整性』→四性；『拟/起草/写一份』→拟稿；"
        "『相关/关联』→关联；『索引/重建/知识库』→知识库；其余一般问答→问答。"
    )

    header = "Content-Type:application/json\nX-User-Token:{{#" + start_id + ".user_token#}}"
    if service_token:
        header += f"\nX-Service-Token:{service_token}"

    # 各分支 LLM 的统一系统提示：兼容"档案条目清单"与"业务规则文本"两类素材，
    # 检索类逐条输出可点击 /archive/reader 链接，有条目绝不说"未找到"。
    def branch_prompt(http_id: str) -> str:
        return (
            "你是 SAMS 档案库问答助手。\n\n"
            "用户问题：{{#sys.query#}}\n\n"
            "后端检索到的真实素材（权威数据，可能是档案条目清单，也可能是业务规则文本）：\n"
            "{{#" + http_id + ".body#}}\n\n"
            "【输出要求】\n"
            "1. 只能基于素材作答，绝不编造素材之外的档案、年度、档号、责任者或结论。\n"
            "2. 若素材是档案条目清单（每行形如 `archive_id | 档号 | 题名 | 年度 | 责任者 | 全宗号`），"
            "逐条输出为带编号的可点击列表，不得遗漏：\n"
            "   1. [题名](/archive/reader?id=该行的archive_id) — 档号 `档号` · 年度 年 · 责任者 责任者\n"
            "   archive_id 只用于拼链接，不要显示给用户。\n"
            "3. 若素材是业务规则/说明文本，用简洁自然的中文作答，Markdown 排版，关键结论 **加粗**。\n"
            "4. 仅当素材明确为『未命中/为空』时，才回复：未检索到相关内容，请补充关键词、年份或全宗号后重试。"
            "素材包含任何条目时绝不能说未找到。\n"
            "5. 不要以『根据…』『以下是…』开头，不要出现『前端/后端/系统/JSON/字段/素材』等技术词。"
        )

    nodes = [
        {
            "id": start_id,
            "type": "custom",
            "data": {
                "type": "start",
                "title": "Start",
                "desc": "",
                "variables": [
                    {"label": "scenario_hint", "variable": "scenario_hint", "type": "text-input", "required": False, "max_length": 32, "options": []},
                    {"label": "citations_json", "variable": "citations_json", "type": "paragraph", "required": False, "max_length": 16384, "options": []},
                    {"label": "tenant_id", "variable": "tenant_id", "type": "text-input", "required": False, "max_length": 64, "options": []},
                    {"label": "user_token", "variable": "user_token", "type": "text-input", "required": False, "max_length": 1024, "options": []},
                ],
            },
            "position": {"x": 80, "y": 280},
            "sourcePosition": "right",
            "targetPosition": "left",
        },
        {
            "id": classifier_id,
            "type": "custom",
            "data": {
                "type": "question-classifier",
                "title": "意图分类",
                "desc": "把用户问题归到对应档案业务场景，路由到该意图分支",
                "query_variable_selector": ["sys", "query"],
                "model": {
                    "provider": "langgenius/ollama/ollama",
                    "name": "qwen2.5:7b",
                    "mode": "chat",
                    "completion_params": {"temperature": 0.1},
                },
                "classes": classifier_classes,
                "instruction": classifier_instruction,
                "instructions": classifier_instruction,
                "topics": [],
                "vision": {"enabled": False},
            },
            "position": {"x": 360, "y": 280},
            "sourcePosition": "right",
            "targetPosition": "left",
        },
    ]

    edges = [
        {
            "id": f"edge_{start_id}_{classifier_id}",
            "source": start_id,
            "sourceHandle": "source",
            "target": classifier_id,
            "targetHandle": "target",
            "type": "custom",
            "data": {"isInIteration": False, "isInLoop": False, "sourceType": "start", "targetType": "question-classifier"},
        }
    ]

    for i, sc in enumerate(SCENARIOS):
        http_id = f"http_{sc.code}"
        llm_id = f"llm_{sc.code}"
        ans_id = f"ans_{sc.code}"
        y = 80 + i * 160

        dispatch_body = json.dumps(
            {
                "tool_name": sc.code,
                "fallback_tool_name": "qa",
                "arguments": {"query": "{{#sys.query#}}", "tenant_id": "{{#" + start_id + ".tenant_id#}}"},
            },
            ensure_ascii=False,
        )

        nodes.append({
            "id": http_id,
            "type": "custom",
            "data": {
                "type": "http-request",
                "title": f"调用后端 · {sc.classifier_label}",
                "desc": f"回调 /tool/dispatch_text（tool_name={sc.code}）取权威数据",
                "method": "post",
                "url": f"{BACKEND_URL_FROM_DIFY}/api/v1/ai/internal/tool/dispatch_text",
                "authorization": {"type": "no-auth", "config": None},
                "headers": header,
                "params": "",
                "body": {"type": "json", "data": [{"key": "", "type": "text", "value": dispatch_body}]},
                "timeout": {"connect": 10, "read": 60, "write": 30},
                "retry_config": {"enabled": False, "max_retries": 1, "retry_interval": 1000, "exponential_backoff": {"enabled": False, "multiplier": 2, "max_interval": 10000}},
            },
            "position": {"x": 660, "y": y},
            "sourcePosition": "right",
            "targetPosition": "left",
        })

        nodes.append({
            "id": llm_id,
            "type": "custom",
            "data": {
                "type": "llm",
                "title": f"{sc.classifier_label} · 整理",
                "desc": "该意图自己的 LLM：把后端权威数据按意图排版并流式输出",
                "model": {
                    "provider": "langgenius/ollama/ollama",
                    "name": "qwen2.5:7b",
                    "mode": "chat",
                    "completion_params": {"temperature": 0.2},
                },
                "prompt_template": [{"role": "system", "text": branch_prompt(http_id)}],
                "memory": {"query_prompt_template": "{{#sys.query#}}", "window": {"enabled": False, "size": 10}},
                "context": {"enabled": False, "variable_selector": []},
                "vision": {"enabled": False},
                "variables": [],
            },
            "position": {"x": 960, "y": y},
            "sourcePosition": "right",
            "targetPosition": "left",
        })

        nodes.append({
            "id": ans_id,
            "type": "custom",
            "data": {
                "type": "answer",
                "title": f"{sc.classifier_label} · Answer",
                "desc": "",
                "answer": "{{#" + llm_id + ".text#}}",
                "variables": [],
            },
            "position": {"x": 1260, "y": y},
            "sourcePosition": "right",
            "targetPosition": "left",
        })

        edges.append({
            "id": f"edge_cls_{sc.code}",
            "source": classifier_id,
            "sourceHandle": sc.code,
            "target": http_id,
            "targetHandle": "target",
            "type": "custom",
            "data": {"isInIteration": False, "isInLoop": False, "sourceType": "question-classifier", "targetType": "http-request"},
        })
        edges.append({
            "id": f"edge_{http_id}_{llm_id}",
            "source": http_id,
            "sourceHandle": "source",
            "target": llm_id,
            "targetHandle": "target",
            "type": "custom",
            "data": {"isInIteration": False, "isInLoop": False, "sourceType": "http-request", "targetType": "llm"},
        })
        edges.append({
            "id": f"edge_{llm_id}_{ans_id}",
            "source": llm_id,
            "sourceHandle": "source",
            "target": ans_id,
            "targetHandle": "target",
            "type": "custom",
            "data": {"isInIteration": False, "isInLoop": False, "sourceType": "llm", "targetType": "answer"},
        })

    return {
        "app": {
            "description": "档案智能体主入口：意图分类 → 各意图独立分支（调后端能力 + 该意图 LLM 整理）→ 流式作答",
            "icon": "robot_face",
            "icon_background": "#E0F2FE",
            "icon_type": "emoji",
            "mode": "advanced-chat",
            "name": "档案智能体（主入口）",
            "use_icon_as_answer_icon": True,
        },
        "dependencies": DIFY_DEPENDENCIES,
        "kind": "app",
        "version": "0.6.0",
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {
                "file_upload": {"enabled": False},
                "opening_statement": "你好！我是 SAMS 档案智能体。我会先判断你的问题属于哪个档案业务场景，再走对应分支为你处理。",
                "retriever_resource": {"enabled": True},
                "sensitive_word_avoidance": {"enabled": False},
                "speech_to_text": {"enabled": False},
                "suggested_questions": ["永久保管期限的档案有哪些？", "查 2024 年的财务凭证", "为 2024 年人事档案生成专题综述"],
                "suggested_questions_after_answer": {"enabled": False},
                "text_to_speech": {"enabled": False, "language": "", "voice": ""},
            },
            "graph": {
                "edges": edges,
                "nodes": nodes,
                "viewport": {"x": 0, "y": 0, "zoom": 0.5},
            },
        },
    }


# ── 子 Workflow 构造 ────────────────────────────────────────────────────────


def build_sub_workflow(scenario: ScenarioMeta) -> dict:
    """子 Workflow：Start(query) → HTTP(回调后端能力 service) → LLM(格式化) → End"""
    start_id = "node_start"
    http_id = "node_http"
    llm_id = "node_llm"
    end_id = "node_end"

    nodes = [
        {
            "id": start_id,
            "type": "custom",
            "data": {
                "type": "start",
                "title": "Start",
                "desc": "",
                "variables": [
                    {
                        "label": "query",
                        "variable": "query",
                        "type": "text-input",
                        "required": True,
                        "max_length": 4096,
                        "options": [],
                    },
                    {
                        "label": "tenant_id",
                        "variable": "tenant_id",
                        "type": "text-input",
                        "required": False,
                        "max_length": 64,
                        "options": [],
                    },
                    {
                        "label": "user_token",
                        "variable": "user_token",
                        "type": "text-input",
                        "required": False,
                        "max_length": 1024,
                        "options": [],
                    },
                ],
            },
            "position": {"x": 80, "y": 200},
            "sourcePosition": "right",
            "targetPosition": "left",
        },
        {
            "id": http_id,
            "type": "custom",
            "data": {
                "type": "http-request",
                "title": f"调用后端 {scenario.code} 能力",
                "desc": f"回调 SAMS 后端 /v1/ai/internal/capability/{scenario.code}",
                "method": "post",
                "url": f"{BACKEND_URL_FROM_DIFY}/api/v1/ai/internal/capability/{scenario.code}",
                "authorization": {
                    "type": "no-auth",
                    "config": None,
                },
                "headers": "Content-Type:application/json\nX-User-Token:{{#" + start_id + ".user_token#}}",
                "params": "",
                "body": {
                    "type": "json",
                    "data": [
                        {
                            "key": "",
                            "type": "text",
                            "value": json.dumps(
                                {
                                    "query": "{{#" + start_id + ".query#}}",
                                    "tenant_id": "{{#" + start_id + ".tenant_id#}}",
                                },
                                ensure_ascii=False,
                            ),
                        }
                    ],
                },
                "timeout": {"connect": 10, "read": 60, "write": 30},
                "retry_config": {
                    "enabled": False,
                    "max_retries": 1,
                    "retry_interval": 1000,
                    "exponential_backoff": {
                        "enabled": False,
                        "multiplier": 2,
                        "max_interval": 10000,
                    },
                },
            },
            "position": {"x": 380, "y": 200},
            "sourcePosition": "right",
            "targetPosition": "left",
        },
        {
            "id": llm_id,
            "type": "custom",
            "data": {
                "type": "llm",
                "title": "答案格式化",
                "desc": "用 LLM 把后端 JSON 结果改写为人类可读答案",
                "model": {
                    "provider": "langgenius/ollama/ollama",
                    "name": "qwen2.5:7b",
                    "mode": "chat",
                    "completion_params": {"temperature": 0.3},
                },
                "prompt_template": [
                    {"role": "system", "text": scenario.sub_workflow_prompt},
                    {"role": "user", "text": "用户问题：{{#" + start_id + ".query#}}\n\n后端结果：{{#" + http_id + ".body#}}"},
                ],
                "memory": None,
                "context": {"enabled": False, "variable_selector": []},
                "vision": {"enabled": False},
                "variables": [],
            },
            "position": {"x": 680, "y": 200},
            "sourcePosition": "right",
            "targetPosition": "left",
        },
        {
            "id": end_id,
            "type": "custom",
            "data": {
                "type": "end",
                "title": "End",
                "desc": "",
                "outputs": [
                    {
                        "value_selector": [llm_id, "text"],
                        "value_type": "string",
                        "variable": "answer",
                    },
                    {
                        "value_selector": [http_id, "body"],
                        "value_type": "string",
                        "variable": "raw",
                    },
                ],
            },
            "position": {"x": 980, "y": 200},
            "sourcePosition": "right",
            "targetPosition": "left",
        },
    ]

    edges = [
        {
            "id": f"edge_{start_id}_{http_id}",
            "source": start_id,
            "sourceHandle": "source",
            "target": http_id,
            "targetHandle": "target",
            "type": "custom",
            "data": {"isInIteration": False, "isInLoop": False, "sourceType": "start", "targetType": "http-request"},
        },
        {
            "id": f"edge_{http_id}_{llm_id}",
            "source": http_id,
            "sourceHandle": "source",
            "target": llm_id,
            "targetHandle": "target",
            "type": "custom",
            "data": {"isInIteration": False, "isInLoop": False, "sourceType": "http-request", "targetType": "llm"},
        },
        {
            "id": f"edge_{llm_id}_{end_id}",
            "source": llm_id,
            "sourceHandle": "source",
            "target": end_id,
            "targetHandle": "target",
            "type": "custom",
            "data": {"isInIteration": False, "isInLoop": False, "sourceType": "llm", "targetType": "end"},
        },
    ]

    return {
        "app": {
            "description": scenario.description,
            "icon": scenario.icon,
            "icon_background": scenario.icon_bg,
            "icon_type": "emoji",
            "mode": "workflow",
            "name": f"wf-{scenario.code}",
            "use_icon_as_answer_icon": False,
        },
        "dependencies": DIFY_DEPENDENCIES,
        "kind": "app",
        "version": "0.6.0",
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {
                "file_upload": {"enabled": False},
                "opening_statement": "",
                "retriever_resource": {"enabled": False},
                "sensitive_word_avoidance": {"enabled": False},
                "speech_to_text": {"enabled": False},
                "suggested_questions": [],
                "suggested_questions_after_answer": {"enabled": False},
                "text_to_speech": {"enabled": False, "language": "", "voice": ""},
            },
            "graph": {
                "edges": edges,
                "nodes": nodes,
                "viewport": {"x": 0, "y": 0, "zoom": 0.7},
            },
        },
    }
