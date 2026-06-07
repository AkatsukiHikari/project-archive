"""
Dify 一键导入脚本（A' 方案：1 主 Chatflow + 8 子 Workflow）

工作流：
  1. 登录 Dify console，拿 cookies + CSRF
  2. 列出当前 workspace 所有 app
  3. 构造 9 个 DSL（1 主 Chatflow + 8 子 Workflow）
  4. 导入 → 拿 App ID → 创建 API Key
  5. YAML 备份到 docs/dify/apps_v2/
  6. API Key 写入 backend/.env.dify_keys 供手动合入 .env

用法：
  uv run python scripts/dify_sync.py
  uv run python scripts/dify_sync.py --force         # 强制删旧重建
  uv run python scripts/dify_sync.py --only qa       # 只处理子 workflow qa
  uv run python scripts/dify_sync.py --only master   # 只处理主 chatflow
"""
from __future__ import annotations

import argparse
import base64
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

import httpx
import yaml

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)


# ── 配置 ────────────────────────────────────────────────────────────────────
DIFY_CONSOLE_URL = os.environ.get("DIFY_CONSOLE_URL", "http://localhost/console/api")
DIFY_EMAIL = os.environ.get("DIFY_CONSOLE_EMAIL", "cloud@admin.com")
DIFY_PASSWORD = os.environ.get("DIFY_CONSOLE_PASSWORD", "Claude2026")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
APPS_DIR = PROJECT_ROOT / "docs" / "dify" / "apps"        # 旧版本 9 chatbot 备份（保留）
APPS_V2_DIR = PROJECT_ROOT / "docs" / "dify" / "apps_v2"  # A' 方案：1 chatflow + 8 workflow
ENV_OUT_PATH = PROJECT_ROOT / "backend" / ".env.dify_keys"

# A' 方案的 9 个 App 名称（顺序：master 主 chatflow + 8 子 workflow）
MASTER_NAME = "档案智能体（主入口）"
SUB_WF_NAMES = {
    "qa": "wf-qa",
    "search": "wf-search",
    "summary": "wf-summary",
    "attach": "wf-attach",
    "catalog": "wf-catalog",
    "fournat": "wf-fournat",
    "draft": "wf-draft",
    "relate": "wf-relate",
    "kb_manage": "wf-kb_manage",
}


# ── 场景定义（每个场景一个独立 Chatbot，独立 prompt + opening + tone） ────────
@dataclass(frozen=True)
class Scenario:
    code: str
    name: str
    description: str
    icon: str
    icon_bg: str
    temperature: float
    opening: str
    pre_prompt: str
    suggested_questions: list[str]


SCENARIOS: list[Scenario] = [
    Scenario(
        code="qa",
        name="档案智能问答",
        description="基于档案知识库的检索增强问答，强制引用，无证据拒答",
        icon="speech_balloon",
        icon_bg="#E0F2FE",
        temperature=0.3,
        opening="你好！我是 SAMS 档案智能问答助手。我会基于档案库内容回答你的问题，并标注每条答案的出处。",
        pre_prompt=(
            "你是 SAMS 档案智能问答助手。\n"
            "回答原则：\n"
            "1. 仅基于用户消息附带的 {{citations}}（业务规则 + 档案元数据）作答；\n"
            "2. 引用必须明确指出来源标题；\n"
            "3. 无证据时回复：『未在知识库中找到相关档案或规则，请补充关键词或时间/全宗号条件。』；\n"
            "4. 涉及绝密档案时拒答；\n"
            "5. 用专业、简洁、有条理的中文输出。"
        ),
        suggested_questions=[
            "永久保管期限的档案有哪些类型？",
            "档号 DH 字段是如何组成的？",
            "四性检测包含哪些内容？",
        ],
    ),
    Scenario(
        code="search",
        name="自然语言检索",
        description="把自然语言查询转成结构化 ES 检索条件，返回命中档案列表",
        icon="mag",
        icon_bg="#FEF3C7",
        temperature=0.2,
        opening="告诉我你要找什么档案，例如「2024 年的财务凭证」或「市档案馆人事任免文件」，我帮你直接定位到列表。",
        pre_prompt=(
            "你是 SAMS 自然语言检索助手。\n"
            "任务：理解用户的自然语言查询，转化成结构化检索意图。\n"
            "输出格式：\n"
            "  ① 推断的检索意图（关键词 / 年度 / 密级 / 全宗号 / 责任者 …）\n"
            "  ② 基于 {{citations}}（已检索到的档案元数据）列出命中档案\n"
            "  ③ 每条档案输出『题名 · 档号 · 年度 · 全宗号』\n"
            "若 citations 为空，提示用户细化条件（时间、机关、关键词）。"
        ),
        suggested_questions=[
            "查 2024 年财务凭证",
            "找市档案馆 2023 年的人事任免文件",
            "数字化建设相关的档案",
        ],
    ),
    Scenario(
        code="summary",
        name="档案专题综述",
        description="按主题、全宗、类目生成专题综述，每段强制带引用",
        icon="memo",
        icon_bg="#FCE7F3",
        temperature=0.4,
        opening="给我一个主题或时间范围，我会基于档案库为你生成专题综述。每段都会标注引用出处。",
        pre_prompt=(
            "你是 SAMS 档案专题综述助手。\n"
            "任务：基于 {{citations}}（业务规则 + 档案元数据）为用户生成一份结构化的专题综述。\n"
            "输出结构：\n"
            "  一、概述（背景与覆盖范围）\n"
            "  二、关键档案与规则（分条列出，每条带出处）\n"
            "  三、结论与建议\n"
            "禁止编造引用之外的信息。若 citations 不足以支撑综述，明确指出缺口。"
        ),
        suggested_questions=[
            "2024 年度财务工作综述",
            "近三年市档案馆数字化建设进展",
            "永久保管档案的管理要点综述",
        ],
    ),
    Scenario(
        code="attach",
        name="档案自动挂接",
        description="读取新材料，匹配候选档案，产出挂接 patch 草案（写类，走审核队列）",
        icon="link",
        icon_bg="#DCFCE7",
        temperature=0.2,
        opening="把新材料的题名、责任者、年度、内容片段告诉我，我帮你匹配到既有档案或目录，并生成挂接 Patch 草案。",
        pre_prompt=(
            "你是 SAMS 档案自动挂接助手。\n"
            "任务：根据用户描述的新材料，结合 {{citations}}（已检索的候选档案元数据），推断最佳挂接目标。\n"
            "输出：\n"
            "  ① 推荐挂接到的目录 / 档案（含档号 / 题名）；\n"
            "  ② 推断依据（年度、责任者、关键词等匹配项）；\n"
            "  ③ 置信度（低/中/高），高置信才能进 auto 闸门。\n"
            "强调：本能力产出的是 staging patch，不直接落库；最终由人工审核队列处理。"
        ),
        suggested_questions=[
            "把这份 2024 年市档案馆财务月报挂接到合适的目录",
            "新材料：人事任免决定 张三 2024-06，匹配候选档案",
        ],
    ),
    Scenario(
        code="catalog",
        name="AI 自动编目",
        description="从档案文本中抽取核心字段（题名/年度/责任者/密级…），产出编目 patch",
        icon="card_index_dividers",
        icon_bg="#E0E7FF",
        temperature=0.2,
        opening="把档案原文或扫描件 OCR 结果发给我，我抽取标准元数据字段（DH/QZH/TM/RZZ/ND/MJ/BGQX）生成编目 Patch。",
        pre_prompt=(
            "你是 SAMS 档案自动编目助手。\n"
            "任务：从用户提供的档案文本中抽取以下核心字段：\n"
            "  TM 题名 / RZZ 责任者 / ND 年度 / WJRQ 文件日期 / MJ 密级 / BGQX 保管期限 / 类目（文书/会计/人事…）\n"
            "硬字段（DH 档号）由后端 NoRule 引擎自动生成，无需推断。\n"
            "输出 JSON：\n"
            "```\n"
            "{ \"TM\": \"...\", \"RZZ\": \"...\", \"ND\": 2024, ... , \"confidence\": 0.85 }\n"
            "```\n"
            "字段不确定时留空，并在最后段说明哪些字段需要人工核对。"
        ),
        suggested_questions=[
            "从这段文字抽取编目字段：「关于成立 2024 年度信息化建设领导小组的通知 · 办公室 · 2024-03-15」",
        ],
    ),
    Scenario(
        code="fournat",
        name="四性检测建议",
        description="对档案做真实性/完整性/可用性/安全性风险提示（建议态，不下判定）",
        icon="shield",
        icon_bg="#FEE2E2",
        temperature=0.3,
        opening="告诉我要检测的档案档号或上传材料元信息，我提示四性风险点供人工审核。",
        pre_prompt=(
            "你是 SAMS 四性检测辅助助手。\n"
            "任务：基于 {{citations}}（档案元数据 + 业务规则）从四个维度逐条给出风险提示：\n"
            "  ① 真实性（来源 / 责任者 / 时间链）\n"
            "  ② 完整性（哈希 / 子文件清单）\n"
            "  ③ 可用性（格式 / 编码 / 可读性）\n"
            "  ④ 安全性（密级标记 / 加密 / 备份）\n"
            "**只提示风险点，不下判定结论。** 用『可能 / 建议 / 需要核对』等措辞，不用『不通过 / 失败』。"
        ),
        suggested_questions=[
            "档号 J001-WS-2024-Y-00014 的四性风险检测",
            "扫描件归档前的常见可用性风险有哪些？",
        ],
    ),
    Scenario(
        code="draft",
        name="拟稿助手",
        description="鉴定意见 / 销毁建议 / 利用报告草稿生成（建议态，落草稿夹）",
        icon="lower_left_fountain_pen",
        icon_bg="#DBEAFE",
        temperature=0.5,
        opening="告诉我要拟的稿件类型（鉴定意见 / 销毁建议 / 利用报告 …）和涉及的档案，我生成草稿供你修改。",
        pre_prompt=(
            "你是 SAMS 档案拟稿助手。\n"
            "任务：基于 {{citations}}（档案元数据 + 业务规则）生成正式公文草稿。\n"
            "输出包括：\n"
            "  ① 标题（符合公文规范）\n"
            "  ② 正文（分条款、引用准确）\n"
            "  ③ 落款建议\n"
            "**草稿不替代正式签发**，用户应复制到正式表单走审批。"
        ),
        suggested_questions=[
            "给一份『2020 年短期保管档案销毁建议』草稿",
            "拟一份『市档案馆 2024 年度档案利用工作报告』",
        ],
    ),
    Scenario(
        code="relate",
        name="跨档案关联",
        description="给定档案，找语义/时间/责任者相关的其他档案（建议态）",
        icon="link",
        icon_bg="#F3E8FF",
        temperature=0.3,
        opening="给我一个档号或主题，我从档案库找出可能相关的其他档案（建议态，仅供参考）。",
        pre_prompt=(
            "你是 SAMS 跨档案关联助手。\n"
            "任务：基于 {{citations}}（已检索到的相关档案）为用户呈现关联建议。\n"
            "输出：\n"
            "  ① 相关档案列表（题名 · 档号 · 关联理由：时间/责任者/主题）；\n"
            "  ② 置信度（实体消歧可能存在歧义）；\n"
            "  ③ 推荐进一步检索的关键词。\n"
            "强调：关联是建议而非结论，用户需自行核实。"
        ),
        suggested_questions=[
            "找跟 J001-WS-2024-Y-00007「全市档案系统升级改造方案」相关的档案",
            "市档案馆数字化建设相关档案的关联图",
        ],
    ),
    Scenario(
        code="kb_manage",
        name="知识库管理",
        description="查询索引状态、触发重建、回答知识库相关问题",
        icon="card_file_box",
        icon_bg="#FEF3C7",
        temperature=0.2,
        opening="问我知识库的状态、覆盖范围，或触发重建。",
        pre_prompt=(
            "你是 SAMS 知识库管理助手。\n"
            "任务：回答用户关于 SAMS 知识库的问题：\n"
            "  ① L1 元数据：全部档案的核心字段，来自 PostgreSQL，自动增量同步到 ES；\n"
            "  ② L4 业务规则：DA/T 标准 + 内部规章，30 条种子数据；\n"
            "  ③ L2 OCR 原文：P3 阶段接入。\n"
            "用户可以通过『重建知识库』触发全量重建。重建操作通过 staging patch 走审核队列。"
        ),
        suggested_questions=[
            "知识库现在有多少档案？",
            "如何重建 L1 元数据索引？",
            "L4 业务规则有哪些类别？",
        ],
    ),
]


# ── 客户端 ──────────────────────────────────────────────────────────────────
class DifyClient:
    def __init__(self, base_url: str, email: str, password: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.client = httpx.Client(timeout=30.0, follow_redirects=False)
        self._login(email, password)

    def _login(self, email: str, password: str) -> None:
        pwd_b64 = base64.b64encode(password.encode()).decode()
        resp = self.client.post(
            f"{self.base_url}/login",
            json={
                "email": email,
                "password": pwd_b64,
                "language": "zh-Hans",
                "remember_me": True,
            },
            headers={"Content-Type": "application/json"},
        )
        resp.raise_for_status()
        # cookies 已经被 client 接住，提取 csrf
        csrf = self.client.cookies.get("csrf_token")
        if not csrf:
            raise RuntimeError("Dify login 未拿到 csrf_token")
        self.client.headers["X-CSRF-Token"] = csrf
        logger.info("Dify 登录成功 email=%s", email)

    def list_apps(self) -> list[dict]:
        items: list[dict] = []
        page = 1
        while True:
            r = self.client.get(f"{self.base_url}/apps", params={"page": page, "limit": 50})
            r.raise_for_status()
            data = r.json()
            items.extend(data.get("data", []))
            if not data.get("has_more"):
                break
            page += 1
        return items

    def import_app(
        self,
        *,
        yaml_content: str,
        name: str,
        description: str,
        icon: str,
        icon_background: str,
        app_id: str | None = None,
    ) -> str:
        body = {
            "mode": "yaml-content",
            "yaml_content": yaml_content,
            "name": name,
            "description": description,
            "icon_type": "emoji",
            "icon": icon,
            "icon_background": icon_background,
        }
        # 传 app_id → Dify 原地覆盖该 app 的 DSL，保留 app 与 API Key（不换 key）
        if app_id:
            body["app_id"] = app_id
        r = self.client.post(f"{self.base_url}/apps/imports", json=body)
        if r.status_code not in (200, 202):
            raise RuntimeError(f"导入失败 {r.status_code}: {r.text[:300]}")
        data = r.json()
        if data.get("status") not in {"completed", "completed-with-warnings", "pending"}:
            raise RuntimeError(f"导入失败 status={data.get('status')}: {data}")
        if data.get("status") == "completed-with-warnings":
            logger.warning("  导入成功但有警告 dsl_version=%s → %s", data.get("imported_dsl_version"), data.get("current_dsl_version"))
        return data["app_id"]

    def delete_app(self, app_id: str) -> None:
        r = self.client.delete(f"{self.base_url}/apps/{app_id}")
        if r.status_code not in (200, 204):
            logger.warning("删除 app %s 失败 %d: %s", app_id, r.status_code, r.text[:200])

    def list_api_keys(self, app_id: str) -> list[dict]:
        r = self.client.get(f"{self.base_url}/apps/{app_id}/api-keys")
        r.raise_for_status()
        return r.json().get("data", [])

    def create_api_key(self, app_id: str) -> str:
        r = self.client.post(f"{self.base_url}/apps/{app_id}/api-keys")
        if r.status_code not in (200, 201):
            raise RuntimeError(f"创建 API Key 失败 {r.status_code}: {r.text[:200]}")
        return r.json()["token"]

    def publish_workflow(self, app_id: str, marked_name: str = "v1") -> None:
        """advanced-chat / workflow 类应用导入后必须 publish 才能通过 API 调用。"""
        r = self.client.post(
            f"{self.base_url}/apps/{app_id}/workflows/publish",
            json={"marked_name": marked_name, "marked_comment": "auto-published by dify_sync"},
        )
        if r.status_code not in (200, 201):
            logger.warning("publish 失败 app_id=%s status=%d: %s", app_id, r.status_code, r.text[:200])


# ── DSL 渲染 ────────────────────────────────────────────────────────────────

OLLAMA_PLUGIN_IDENT = (
    "langgenius/ollama:0.1.3@"
    "66e156c4f612964c131c49168882e78c2cdfe366879506b97ad855b23c5d6d98"
)


def render_yaml(scenario: Scenario) -> str:
    """直接构造 DSL dict，避免字符串模板冲突。"""
    spec = {
        "app": {
            "description": scenario.description,
            "icon": scenario.icon,
            "icon_background": scenario.icon_bg,
            "icon_type": "emoji",
            "mode": "chat",
            "name": scenario.name,
            "use_icon_as_answer_icon": True,
        },
        "dependencies": [
            {
                "current_identifier": None,
                "type": "marketplace",
                "value": {
                    "marketplace_plugin_unique_identifier": OLLAMA_PLUGIN_IDENT,
                    "version": None,
                },
            }
        ],
        "kind": "app",
        "model_config": {
            "agent_mode": {
                "enabled": False,
                "max_iteration": 10,
                "strategy": "react",
                "tools": [],
            },
            "annotation_reply": {"enabled": False},
            "chat_prompt_config": {"prompt": [{"role": "system", "text": ""}]},
            "completion_prompt_config": {
                "conversation_histories_role": {"assistant_prefix": "", "user_prefix": ""},
                "prompt": {"text": ""},
            },
            "dataset_configs": {
                "datasets": {"datasets": []},
                "retrieval_model": "multiple",
                "top_k": 4,
            },
            "dataset_query_variable": "",
            "external_data_tools": [],
            "file_upload": {
                "allowed_file_extensions": [],
                "allowed_file_types": [],
                "allowed_file_upload_methods": [],
                "enabled": False,
                "image": {
                    "detail": "high",
                    "enabled": False,
                    "number_limits": 3,
                    "transfer_methods": ["remote_url", "local_file"],
                },
                "number_limits": 3,
            },
            "model": {
                "completion_params": {"stop": [], "temperature": scenario.temperature},
                "mode": "chat",
                "name": "qwen2.5:7b",
                "provider": "langgenius/ollama/ollama",
            },
            "more_like_this": {"enabled": False},
            "opening_statement": scenario.opening,
            "pre_prompt": scenario.pre_prompt,
            "prompt_type": "simple",
            "retriever_resource": {"enabled": True},
            "sensitive_word_avoidance": {"config": {}, "enabled": False, "type": ""},
            "speech_to_text": {"enabled": False},
            "suggested_questions": list(scenario.suggested_questions),
            "suggested_questions_after_answer": {"enabled": False},
            "text_to_speech": {"enabled": False, "language": "", "voice": ""},
            "user_input_form": [
                {
                    "paragraph": {
                        "label": "检索证据 (citations)",
                        "variable": "citations",
                        "required": False,
                        "default": "",
                    }
                },
                {
                    "text-input": {
                        "label": "场景代码 (scenario_code)",
                        "variable": "scenario_code",
                        "required": False,
                        "default": "",
                    }
                },
                {
                    "text-input": {
                        "label": "模型档位 (model_tier)",
                        "variable": "model_tier",
                        "required": False,
                        "default": "",
                    }
                },
            ],
        },
        "version": "0.6.0",
    }
    return yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)


# ── 主流程 ──────────────────────────────────────────────────────────────────


def _dump_yaml(spec: dict, dest: Path) -> str:
    dest.parent.mkdir(parents=True, exist_ok=True)
    yml = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)
    dest.write_text(yml, encoding="utf-8")
    return yml


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--force", action="store_true", help="同名 App 存在时先删除再重建")
    parser.add_argument("--only", default=None, help="只处理：master 或 子 wf scenario_code")
    args = parser.parse_args()

    # A' 方案的 builder 模块
    from dify_dsl_builders import SCENARIOS as V2_SCENARIOS, build_master_chatflow, build_sub_workflow

    APPS_V2_DIR.mkdir(parents=True, exist_ok=True)

    # 1) 生成所有 YAML 并备份
    #    若配置了 AI_SERVICE_TOKEN，则把它烘焙进 dispatch 节点的 X-Service-Token 头，
    #    作为 Dify→后端的稳定调用方鉴权（与会话级 user_token 解耦，后者只携带身份）。
    _service_token = os.getenv("AI_SERVICE_TOKEN", "")
    master_spec = build_master_chatflow(service_token=_service_token)
    master_yaml = _dump_yaml(master_spec, APPS_V2_DIR / "master_chatflow.yml")
    logger.info("YAML 备份 → docs/dify/apps_v2/master_chatflow.yml")

    sub_yamls: dict[str, tuple[ScenarioMetaLike, str]] = {}
    for sc in V2_SCENARIOS:
        spec = build_sub_workflow(sc)
        ymlc = _dump_yaml(spec, APPS_V2_DIR / f"wf_{sc.code}.yml")
        sub_yamls[sc.code] = (sc, ymlc)
        logger.info("YAML 备份 → docs/dify/apps_v2/wf_%s.yml", sc.code)

    # 2) 登录 Dify
    cli = DifyClient(DIFY_CONSOLE_URL, DIFY_EMAIL, DIFY_PASSWORD)
    existing = {a["name"]: a for a in cli.list_apps()}
    logger.info("Dify 现有 app 数：%d", len(existing))

    keys: dict[str, str] = {}

    def _ensure(name: str, yaml_content: str, description: str, icon: str, icon_bg: str) -> str:
        existed = existing.get(name)
        if existed and args.force:
            logger.info("--force 删除旧 app %s id=%s", name, existed["id"])
            cli.delete_app(existed["id"])
            existed = None
        if existed:
            # 原地覆盖 DSL：保留 app 与 API Key，无需改 .env
            app_id = cli.import_app(
                yaml_content=yaml_content,
                name=name,
                description=description,
                icon=icon,
                icon_background=icon_bg,
                app_id=existed["id"],
            )
            logger.info("原地更新 %s id=%s（保留 API Key）", name, app_id)
        else:
            app_id = cli.import_app(
                yaml_content=yaml_content,
                name=name,
                description=description,
                icon=icon,
                icon_background=icon_bg,
            )
            logger.info("导入新 app %s id=%s", name, app_id)
        api_keys = cli.list_api_keys(app_id)
        if api_keys:
            token = api_keys[0]["token"]
            logger.info("  → 复用现有 API Key %s...", token[:14])
        else:
            token = cli.create_api_key(app_id)
            logger.info("  → 新建 API Key %s...", token[:14])
        # Workflow 类应用必须 publish 才能通过 API 调用
        cli.publish_workflow(app_id)
        logger.info("  → publish OK")
        return token

    # 3) 主 Chatflow
    if not args.only or args.only == "master":
        keys["MASTER"] = _ensure(
            MASTER_NAME,
            master_yaml,
            description=master_spec["app"]["description"],
            icon=master_spec["app"]["icon"],
            icon_bg=master_spec["app"]["icon_background"],
        )

    # 4) 子 Workflow（按场景）
    for code, (sc, ymlc) in sub_yamls.items():
        if args.only and args.only != "master" and args.only != code:
            continue
        if args.only == "master":
            break
        wf_name = SUB_WF_NAMES[code]
        keys[code] = _ensure(
            wf_name,
            ymlc,
            description=sc.description,
            icon=sc.icon,
            icon_bg=sc.icon_bg,
        )

    # 5) 输出 .env.dify_keys
    lines = [
        "# A' 方案：1 主 Chatflow + 8 子 Workflow API Key（由 scripts/dify_sync.py 自动生成）",
        "# 复制到 backend/.env",
        "",
    ]
    if "MASTER" in keys:
        lines.append(f"DIFY_MASTER_API_KEY={keys['MASTER']}")
        lines.append("")
    for code in [c for c in keys if c != "MASTER"]:
        lines.append(f"DIFY_WF_API_KEY_{code.upper()}={keys[code]}")
    ENV_OUT_PATH.write_text("\n".join(lines) + "\n", encoding="utf-8")
    logger.info("API Keys 已写入 → %s", ENV_OUT_PATH.relative_to(PROJECT_ROOT))

    print("\n=========================")
    print("Dify A' 方案同步完成 ✓")
    if "MASTER" in keys:
        print(f"  - 主 Chatflow: 「{MASTER_NAME}」")
    print(f"  - 子 Workflow 数: {sum(1 for k in keys if k != 'MASTER')}")
    print(f"  - YAML 备份: docs/dify/apps_v2/")
    print(f"  - API Key 文件: backend/.env.dify_keys")
    print("=========================")
    return 0


# 让 build_sub_workflow 的 dataclass 在主流程里能用类型；避免循环 import
ScenarioMetaLike = object


if __name__ == "__main__":
    sys.exit(main())
