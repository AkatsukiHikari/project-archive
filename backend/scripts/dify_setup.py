"""AI 重构：在 Dify 里建立 2 个干净的 App + 删旧。

- OCR 工作流：Start(file) → MinerU parse-file(开 OCR) → End(text)
- 问答 Chatflow：Start → 知识检索(档案知识库) → DeepSeek(结合 ES 上下文) → Answer
- 删除所有旧的乱七八糟 App
- 创建「档案知识库」dataset

用法：
  PYTHONPATH=. uv run python scripts/dify_setup.py --ocr           # 仅建 OCR 工作流（验证）
  PYTHONPATH=. uv run python scripts/dify_setup.py --all --purge   # 删旧 + 建 dataset + 两个 App
环境变量：DIFY_CONSOLE_URL / DIFY_CONSOLE_EMAIL / DIFY_CONSOLE_PASSWORD
"""

import argparse
import base64
import os

import httpx
import yaml

CONSOLE = os.environ.get("DIFY_CONSOLE_URL", "http://localhost/console/api").rstrip("/")
EMAIL = os.environ.get("DIFY_CONSOLE_EMAIL", "cloud@admin.com")
PASSWORD = os.environ.get("DIFY_CONSOLE_PASSWORD", "Claude2026")

DEEPSEEK_PROVIDER = "langgenius/deepseek/deepseek"
DEEPSEEK_MODEL = "deepseek-chat"
MINERU_PROVIDER = "langgenius/mineru/mineru"


# ── Dify console 客户端 ────────────────────────────────────────────────────────


class Dify:
    def __init__(self):
        self.c = httpx.Client(timeout=60.0, follow_redirects=False)
        r = self.c.post(
            f"{CONSOLE}/login",
            json={
                "email": EMAIL,
                "password": base64.b64encode(PASSWORD.encode()).decode(),
                "language": "zh-Hans",
                "remember_me": True,
            },
        )
        r.raise_for_status()
        tok = (r.json().get("data") or {}).get("access_token")
        if tok:
            self.c.headers["Authorization"] = f"Bearer {tok}"
        csrf = self.c.cookies.get("csrf_token")
        if csrf:
            self.c.headers["X-CSRF-Token"] = csrf

    def list_apps(self):
        out, page = [], 1
        while True:
            d = self.c.get(
                f"{CONSOLE}/apps", params={"page": page, "limit": 100}
            ).json()
            out += d.get("data", [])
            if not d.get("has_more"):
                break
            page += 1
        return out

    def delete_app(self, app_id):
        self.c.delete(f"{CONSOLE}/apps/{app_id}")

    def import_app(self, spec, name, description, icon="robot_face", icon_bg="#E0F2FE"):
        yaml_content = yaml.safe_dump(spec, allow_unicode=True, sort_keys=False)
        r = self.c.post(
            f"{CONSOLE}/apps/imports",
            json={
                "mode": "yaml-content",
                "yaml_content": yaml_content,
                "name": name,
                "description": description,
                "icon_type": "emoji",
                "icon": icon,
                "icon_background": icon_bg,
            },
        )
        if r.status_code not in (200, 202):
            raise RuntimeError(f"导入失败 {r.status_code}: {r.text[:400]}")
        data = r.json()
        if data.get("status") not in {
            "completed",
            "completed-with-warnings",
            "pending",
        }:
            raise RuntimeError(
                f"导入失败 status={data.get('status')}: {str(data)[:400]}"
            )
        if data.get("status") == "completed-with-warnings":
            print(
                f"  ⚠ 导入有警告：{data.get('imported_dsl_version')} → {data.get('current_dsl_version')}"
            )
        return data["app_id"]

    def publish(self, app_id):
        r = self.c.post(
            f"{CONSOLE}/apps/{app_id}/workflows/publish",
            json={"marked_name": "v1", "marked_comment": "dify_setup"},
        )
        if r.status_code not in (200, 201):
            print(f"  ⚠ publish 失败 {r.status_code}: {r.text[:200]}")

    def api_key(self, app_id):
        keys = self.c.get(f"{CONSOLE}/apps/{app_id}/api-keys").json().get("data", [])
        if keys:
            return keys[0]["token"]
        return self.c.post(f"{CONSOLE}/apps/{app_id}/api-keys").json()["token"]

    def create_dataset(self, name):
        # 已存在则复用
        ds = self.c.get(f"{CONSOLE}/datasets", params={"page": 1, "limit": 100}).json()
        for d in ds.get("data", []):
            if d.get("name") == name:
                return d["id"]
        # 空知识库只接受 name（indexing_technique 在首次加文档时才定）
        r = self.c.post(f"{CONSOLE}/datasets", json={"name": name})
        if r.status_code not in (200, 201):
            raise RuntimeError(f"建 dataset 失败 {r.status_code}: {r.text[:300]}")
        return r.json()["id"]

    def dataset_api_key(self):
        r = self.c.get(f"{CONSOLE}/datasets/api-keys")
        keys = r.json().get("data", []) if r.status_code == 200 else []
        if keys:
            return keys[0]["token"]
        r = self.c.post(f"{CONSOLE}/datasets/api-keys")
        return r.json().get("token", "")


# ── DSL 构造 ───────────────────────────────────────────────────────────────────


def _node(nid, ntype, data, x, y):
    return {
        "id": nid,
        "type": "custom",
        "data": {
            "type": ntype,
            "title": data.pop("title", ntype),
            "desc": data.pop("desc", ""),
            **data,
        },
        "position": {"x": x, "y": y},
        "sourcePosition": "right",
        "targetPosition": "left",
    }


def _edge(src, tgt, st, tt):
    return {
        "id": f"edge_{src}_{tgt}",
        "source": src,
        "sourceHandle": "source",
        "target": tgt,
        "targetHandle": "target",
        "type": "custom",
        "data": {
            "isInIteration": False,
            "isInLoop": False,
            "sourceType": st,
            "targetType": tt,
        },
    }


def build_ocr_workflow():
    start, tool, end = "node_start", "node_mineru", "node_end"
    nodes = [
        _node(
            start,
            "start",
            {
                "title": "Start",
                "variables": [
                    {
                        "label": "档案文件",
                        "variable": "file",
                        "type": "file",
                        "required": True,
                        "allowed_file_types": ["document"],
                        "allowed_file_extensions": [".PDF", ".pdf", ".OFD", ".ofd"],
                        "allowed_file_upload_methods": ["local_file", "remote_url"],
                        "options": [],
                    }
                ],
            },
            80,
            240,
        ),
        _node(
            tool,
            "tool",
            {
                "title": "MinerU 解析(OCR)",
                "provider_id": MINERU_PROVIDER,
                "provider_name": MINERU_PROVIDER,
                "provider_type": "builtin",
                "provider_label": "MinerU",
                "tool_name": "parse-file",
                "tool_label": "parse-file",
                "is_team_authorization": True,
                "tool_configurations": {
                    "parse_method": "auto",
                    "enable_ocr": True,
                    "enable_table": True,
                    "enable_formula": True,
                    "language": "auto",
                    "model_version": "pipeline",
                    "backend": "pipeline",
                },
                "tool_parameters": {
                    "file": {"type": "variable", "value": [start, "file"]},
                },
                "output_schema": None,
            },
            380,
            240,
        ),
        _node(
            end,
            "end",
            {
                "title": "End",
                "outputs": [{"variable": "text", "value_selector": [tool, "text"]}],
            },
            680,
            240,
        ),
    ]
    edges = [_edge(start, tool, "start", "tool"), _edge(tool, end, "tool", "end")]
    return _app(
        "workflow",
        "档案OCR工作流",
        "挂接PDF时用MinerU识别全文",
        nodes,
        edges,
        icon="page_facing_up",
        icon_bg="#FEF3C7",
    )


def build_qa_chatflow(dataset_id):
    start, kr, llm, ans = "node_start", "node_kr", "node_llm", "node_answer"
    prompt = (
        "你是 SAMS 档案馆智能助手。资料分两部分：\n"
        "① 后端 ES 精确检索到的相关档案（**权威**，含档号与原文）：\n"
        "{{#" + start + ".es_context#}}\n\n"
        "② 知识库语义召回的补充内容：\n{{#" + kr + ".result#}}\n\n"
        "用户问题：{{#sys.query#}}\n\n"
        "【要求】优先依据①的权威档案作答，②作补充；逐条标注来源〔档号〕；"
        "资料不足就如实说明，绝不编造档号/年度/结论。"
    )
    nodes = [
        _node(
            start,
            "start",
            {
                "title": "Start",
                "variables": [
                    {
                        "label": "ES检索上下文",
                        "variable": "es_context",
                        "type": "paragraph",
                        "required": False,
                        "max_length": 48000,
                        "options": [],
                    },
                ],
            },
            80,
            240,
        ),
        _node(
            kr,
            "knowledge-retrieval",
            {
                "title": "知识检索",
                "query_variable_selector": ["sys", "query"],
                "dataset_ids": [dataset_id],
                "retrieval_mode": "multiple",
                "multiple_retrieval_config": {
                    "top_k": 6,
                    "score_threshold": None,
                    "score_threshold_enabled": False,
                    "reranking_enable": False,
                    "reranking_mode": "weighted_score",
                    "weights": {
                        "weight_type": "customized",
                        "vector_setting": {
                            "vector_weight": 0.7,
                            "embedding_provider_name": "",
                            "embedding_model_name": "",
                        },
                        "keyword_setting": {"keyword_weight": 0.3},
                    },
                    "reranking_model": {"provider": "", "model": ""},
                },
            },
            360,
            240,
        ),
        _node(
            llm,
            "llm",
            {
                "title": "DeepSeek 作答",
                "model": {
                    "provider": DEEPSEEK_PROVIDER,
                    "name": DEEPSEEK_MODEL,
                    "mode": "chat",
                    "completion_params": {"temperature": 0.3},
                },
                "prompt_template": [{"role": "system", "text": prompt}],
                "context": {"enabled": True, "variable_selector": [kr, "result"]},
                "memory": {
                    "query_prompt_template": "{{#sys.query#}}",
                    "window": {"enabled": False, "size": 10},
                },
                "vision": {"enabled": False},
                "variables": [],
            },
            660,
            240,
        ),
        _node(
            ans,
            "answer",
            {"title": "Answer", "answer": "{{#" + llm + ".text#}}", "variables": []},
            960,
            240,
        ),
    ]
    edges = [
        _edge(start, kr, "start", "knowledge-retrieval"),
        _edge(kr, llm, "knowledge-retrieval", "llm"),
        _edge(llm, ans, "llm", "answer"),
    ]
    return _app(
        "advanced-chat",
        "档案问答",
        "ES精确检索 + 知识库召回 + DeepSeek 作答",
        nodes,
        edges,
        icon="speech_balloon",
        icon_bg="#E0F2FE",
    )


def build_research_chatflow(dataset_id):
    """编研起草 Chatflow：Start(es_context/title/result_type) + sys.query(用户写作要求)
    → 知识检索(档案知识库) → LLM 成文 → Answer。

    导入后提示词/模型在 Dify UI 内维护；DSL 中的模型字段仅为导入所需初始值。
    """
    start, kr, llm, ans = "node_start", "node_kr", "node_llm", "node_answer"
    prompt = (
        "你是档案编研专家，请按用户的写作要求撰写一篇编研文章（类似研究文章）。\n\n"
        "成果信息：《{{#" + start + ".title#}}》（体裁：{{#" + start + ".result_type#}}）\n\n"
        "参考资料①（后端检索的馆藏档案原文，权威）：\n{{#" + start + ".es_context#}}\n\n"
        "参考资料②（知识库语义召回补充）：\n{{#" + kr + ".result#}}\n\n"
        "用户写作要求：{{#sys.query#}}\n\n"
        "【要求】自然成文、叙述连贯，可用 Markdown 小标题（##）组织；"
        "不要输出清单、表格，也不要逐条罗列档案条目；"
        "所有史实、数字、人名、日期须出自参考资料，引用具体史实在句末标注〔档号〕；"
        "资料未涉及之处如实说明，不得编造。\n"
        "先写一句内容提要（以「提要：」开头），空一行后写正文（Markdown）。"
    )
    nodes = [
        _node(
            start,
            "start",
            {
                "title": "Start",
                "variables": [
                    {"label": "参考资料", "variable": "es_context", "type": "paragraph",
                     "required": False, "max_length": 48000, "options": []},
                    {"label": "成果标题", "variable": "title", "type": "text-input",
                     "required": False, "max_length": 256, "options": []},
                    {"label": "体裁", "variable": "result_type", "type": "text-input",
                     "required": False, "max_length": 64, "options": []},
                ],
            },
            80, 240,
        ),
        _node(
            kr,
            "knowledge-retrieval",
            {
                "title": "知识检索",
                "query_variable_selector": ["sys", "query"],
                "dataset_ids": [dataset_id],
                "retrieval_mode": "multiple",
                "multiple_retrieval_config": {
                    "top_k": 6,
                    "score_threshold": None,
                    "score_threshold_enabled": False,
                    "reranking_enable": False,
                    "reranking_mode": "weighted_score",
                    "weights": {
                        "weight_type": "customized",
                        "vector_setting": {
                            "vector_weight": 0.7,
                            "embedding_provider_name": "",
                            "embedding_model_name": "",
                        },
                        "keyword_setting": {"keyword_weight": 0.3},
                    },
                    "reranking_model": {"provider": "", "model": ""},
                },
            },
            360, 240,
        ),
        _node(
            llm,
            "llm",
            {
                "title": "AI 成文",
                # DSL 导入要求提供初始模型，导入后在 Dify UI 更换
                "model": {
                    "provider": DEEPSEEK_PROVIDER,
                    "name": DEEPSEEK_MODEL,
                    "mode": "chat",
                    "completion_params": {"temperature": 0.4},
                },
                "prompt_template": [{"role": "system", "text": prompt}],
                "context": {"enabled": True, "variable_selector": [kr, "result"]},
                "memory": {
                    "query_prompt_template": "{{#sys.query#}}",
                    "window": {"enabled": False, "size": 10},
                },
                "vision": {"enabled": False},
                "variables": [],
            },
            660, 240,
        ),
        _node(
            ans,
            "answer",
            {"title": "Answer", "answer": "{{#" + llm + ".text#}}", "variables": []},
            960, 240,
        ),
    ]
    edges = [
        _edge(start, kr, "start", "knowledge-retrieval"),
        _edge(kr, llm, "knowledge-retrieval", "llm"),
        _edge(llm, ans, "llm", "answer"),
    ]
    return _app(
        "advanced-chat",
        "编研起草",
        "按用户写作要求，基于知识库+馆藏原文生成编研文章（提示词在本应用内管理）",
        nodes,
        edges,
        icon="fountain_pen",
        icon_bg="#FCE7F3",
    )


def build_catalog_workflow():
    """智能著录抽取：Start(全文+字段schema+当前条目) → DeepSeek 抽结构化JSON → End(text)。"""
    start, llm, end = "node_start", "node_llm", "node_end"
    prompt = (
        "你是档案著录专家。请依据『档案原文全文』，按『目标字段定义』抽取每个字段的著录值。\n\n"
        "目标字段定义(JSON，name=字段名/拼音缩写，label=中文名，type=类型，"
        "required=是否必录，options=可选值列表)：\n{{#" + start + ".field_schema#}}\n\n"
        "当前条目已有值(JSON，供参考，可能为空或有误)：\n{{#" + start + ".existing#}}\n\n"
        "档案原文全文：\n{{#" + start + ".full_text#}}\n\n"
        "【要求】\n"
        "1. 只输出一个 JSON 对象，键为字段 name，值为对象 "
        "{\"value\": 抽取值, \"confidence\": 0~100 整数, \"evidence\": 原文出处片段}。\n"
        "2. type=select 的字段，value 必须取自该字段 options，否则留空。\n"
        "3. 原文中找不到依据的字段，value 用空字符串、confidence=0。\n"
        "4. 不要编造；日期统一 YYYY-MM-DD；不要输出 JSON 以外的任何文字。"
    )
    nodes = [
        _node(
            start,
            "start",
            {
                "title": "Start",
                "variables": [
                    {"label": "原文全文", "variable": "full_text", "type": "paragraph",
                     "required": True, "max_length": 48000, "options": []},
                    {"label": "字段定义", "variable": "field_schema", "type": "paragraph",
                     "required": True, "max_length": 8000, "options": []},
                    {"label": "当前条目", "variable": "existing", "type": "paragraph",
                     "required": False, "max_length": 8000, "options": []},
                ],
            },
            80, 240,
        ),
        _node(
            llm,
            "llm",
            {
                "title": "DeepSeek 抽取",
                "model": {
                    "provider": DEEPSEEK_PROVIDER,
                    "name": DEEPSEEK_MODEL,
                    "mode": "chat",
                    "completion_params": {"temperature": 0.1},
                },
                "prompt_template": [{"role": "system", "text": prompt}],
                "context": {"enabled": False, "variable_selector": []},
                "vision": {"enabled": False},
                "variables": [],
            },
            420, 240,
        ),
        _node(
            end,
            "end",
            {"title": "End", "outputs": [{"variable": "text", "value_selector": [llm, "text"]}]},
            760, 240,
        ),
    ]
    edges = [_edge(start, llm, "start", "llm"), _edge(llm, end, "llm", "end")]
    return _app(
        "workflow",
        "智能著录抽取",
        "DeepSeek 从原文全文按字段schema抽结构化著录数据",
        nodes,
        edges,
        icon="memo",
        icon_bg="#DCFCE7",
    )


def _app(mode, name, desc, nodes, edges, icon, icon_bg):
    return {
        "app": {
            "description": desc,
            "icon": icon,
            "icon_background": icon_bg,
            "icon_type": "emoji",
            "mode": mode,
            "name": name,
            "use_icon_as_answer_icon": True,
        },
        "dependencies": [],
        "kind": "app",
        "version": "0.6.0",
        "workflow": {
            "conversation_variables": [],
            "environment_variables": [],
            "features": {
                "file_upload": {"enabled": False},
                "opening_statement": "",
                "retriever_resource": {"enabled": True},
                "sensitive_word_avoidance": {"enabled": False},
                "speech_to_text": {"enabled": False},
                "suggested_questions": [],
                "suggested_questions_after_answer": {"enabled": False},
                "text_to_speech": {"enabled": False, "language": "", "voice": ""},
            },
            "graph": {
                "edges": edges,
                "nodes": nodes,
                "viewport": {"x": 0, "y": 0, "zoom": 0.6},
            },
        },
    }


# ── 主流程 ─────────────────────────────────────────────────────────────────────


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--ocr", action="store_true", help="仅建 OCR 工作流")
    ap.add_argument("--all", action="store_true", help="删旧 + dataset + 两个 App")
    ap.add_argument("--purge", action="store_true", help="删除所有旧 App")
    ap.add_argument("--qa", help="重建问答 Chatflow（传 dataset_id），不动其它")
    ap.add_argument("--catalog", action="store_true", help="建/重建 智能著录抽取工作流")
    ap.add_argument("--research", help="建/重建 编研起草 Chatflow（传 dataset_id）")
    args = ap.parse_args()

    dify = Dify()
    print(f"✓ 登录 {EMAIL}")

    if args.research:
        for a in dify.list_apps():
            if a.get("name") == "编研起草":
                dify.delete_app(a["id"])
        app_id = dify.import_app(
            build_research_chatflow(args.research),
            "编研起草",
            "research draft",
            icon="fountain_pen",
            icon_bg="#FCE7F3",
        )
        dify.publish(app_id)
        print(f"✓ 编研起草 Chatflow app_id={app_id}")
        print(f"  DIFY_API_KEY_RESEARCH={dify.api_key(app_id)}")
        return

    if args.catalog:
        for a in dify.list_apps():
            if a.get("name") == "智能著录抽取":
                dify.delete_app(a["id"])
        app_id = dify.import_app(
            build_catalog_workflow(),
            "智能著录抽取",
            "catalog extract",
            icon="memo",
            icon_bg="#DCFCE7",
        )
        dify.publish(app_id)
        print(f"✓ 智能著录工作流 app_id={app_id}")
        print(f"  DIFY_CATALOG_WORKFLOW_KEY={dify.api_key(app_id)}")
        return

    if args.qa:
        for a in dify.list_apps():
            if a.get("name") == "档案问答":
                dify.delete_app(a["id"])
        app_id = dify.import_app(
            build_qa_chatflow(args.qa),
            "档案问答",
            "QA chatflow",
            icon="speech_balloon",
            icon_bg="#E0F2FE",
        )
        dify.publish(app_id)
        print(f"✓ 问答 Chatflow app_id={app_id}")
        print(f"  DIFY_QA_API_KEY={dify.api_key(app_id)}")
        return

    if args.purge or args.all:
        # 清空所有旧 App（这台 Dify 里全是档案 AI 的旧 mess），再建干净的 2 个
        for a in dify.list_apps():
            dify.delete_app(a["id"])
            print(f"  删除旧 App: {a.get('name')}")

    dataset_id = ""
    if args.all:
        dataset_id = dify.create_dataset("档案知识库")
        print(f"✓ 知识库 dataset_id={dataset_id}")
        dskey = dify.dataset_api_key()
        print(f"  DIFY_DATASET_API_KEY={dskey}")

    if args.ocr or args.all:
        app_id = dify.import_app(
            build_ocr_workflow(),
            "档案OCR工作流",
            "MinerU OCR",
            icon="page_facing_up",
            icon_bg="#FEF3C7",
        )
        dify.publish(app_id)
        print(f"✓ OCR 工作流 app_id={app_id}")
        print(f"  DIFY_OCR_WORKFLOW_KEY={dify.api_key(app_id)}")

    if args.all:
        app_id = dify.import_app(
            build_qa_chatflow(dataset_id),
            "档案问答",
            "QA chatflow",
            icon="speech_balloon",
            icon_bg="#E0F2FE",
        )
        dify.publish(app_id)
        print(f"✓ 问答 Chatflow app_id={app_id}")
        print(f"  DIFY_QA_API_KEY={dify.api_key(app_id)}")
        print(f"  DIFY_ARCHIVE_DATASET_ID={dataset_id}")


if __name__ == "__main__":
    main()
