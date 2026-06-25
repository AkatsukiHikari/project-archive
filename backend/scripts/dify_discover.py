"""Dify 环境探测：登录 console，列出 apps / 模型 / 工具 / 知识库。

用于在生成新 DSL 前拿到真实标识（DeepSeek 模型、MinerU 工具、dataset id），
避免凭空猜节点配置。

运行：cd backend && PYTHONPATH=. uv run python scripts/dify_discover.py
环境变量：DIFY_CONSOLE_URL / DIFY_CONSOLE_EMAIL / DIFY_CONSOLE_PASSWORD
"""

import base64
import json
import os

import httpx

CONSOLE = os.environ.get("DIFY_CONSOLE_URL", "http://localhost/console/api").rstrip("/")
EMAIL = os.environ.get("DIFY_CONSOLE_EMAIL", "cloud@admin.com")
PASSWORD = os.environ.get("DIFY_CONSOLE_PASSWORD", "Claude2026")


def _login(client: httpx.Client) -> None:
    r = client.post(
        f"{CONSOLE}/login",
        json={
            "email": EMAIL,
            "password": base64.b64encode(PASSWORD.encode()).decode(),
            "language": "zh-Hans",
            "remember_me": True,
        },
    )
    r.raise_for_status()
    # 新版 Dify 登录返回 access_token；旧版用 cookie+csrf
    data = r.json()
    token = (
        (data.get("data") or {}).get("access_token")
        if isinstance(data.get("data"), dict)
        else None
    )
    if token:
        client.headers["Authorization"] = f"Bearer {token}"
    csrf = client.cookies.get("csrf_token")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    print(f"✓ 登录成功 {EMAIL}")


def _get(client: httpx.Client, path: str):
    try:
        r = client.get(f"{CONSOLE}{path}")
        if r.status_code == 200:
            return r.json()
        return {"_status": r.status_code, "_body": r.text[:200]}
    except Exception as e:  # noqa: BLE001
        return {"_error": str(e)}


def main() -> int:
    client = httpx.Client(timeout=30.0, follow_redirects=False)
    try:
        _login(client)
    except Exception as e:  # noqa: BLE001
        print(
            f"✗ 登录失败：{e}\n  检查 DIFY_CONSOLE_URL/EMAIL/PASSWORD，以及 Dify 是否在 {CONSOLE} 可达"
        )
        return 1

    print("\n━━━ 现有 Apps（旧的将删除）━━━")
    apps = _get(client, "/apps?page=1&limit=100")
    for a in apps.get("data") or []:
        print(f"  [{a.get('mode')}] {a.get('name')}  id={a.get('id')}")

    print("\n━━━ 模型供应商 / LLM（找 DeepSeek）━━━")
    providers = _get(client, "/workspaces/current/model-providers")
    for p in providers.get("data") or []:
        name = p.get("provider")
        if name and (
            "deepseek" in name.lower()
            or "openai" in name.lower()
            or p.get("preferred_provider_type")
        ):
            print(
                f"  provider={name}  label={(p.get('label') or {}).get('zh_Hans') or (p.get('label') or {}).get('en_US')}"
            )
    llms = _get(client, "/workspaces/current/models/model-types/llm")
    for prov in llms.get("data") or []:
        for m in prov.get("models") or []:
            if (
                "deepseek" in (m.get("model") or "").lower()
                or "deepseek" in (prov.get("provider") or "").lower()
            ):
                print(f"  LLM: provider={prov.get('provider')}  model={m.get('model')}")

    print("\n━━━ 工具（找 MinerU）━━━")
    for kind in ("builtin", "api", "workflow", "plugin", "mcp"):
        tools = _get(client, f"/workspaces/current/tools/{kind}")
        items = (
            tools
            if isinstance(tools, list)
            else (tools.get("data") if isinstance(tools, dict) else [])
        )
        for t in items or []:
            if not isinstance(t, dict):
                continue
            blob = json.dumps(t, ensure_ascii=False).lower()
            if "mineru" in blob or "ocr" in blob:
                print(
                    f"  [{kind}] provider name={t.get('name')} id={t.get('id')} plugin={t.get('plugin_id') or t.get('plugin_unique_identifier')}"
                )
                for tool in t.get("tools") or []:
                    if not isinstance(tool, dict):
                        continue
                    print(f"    tool: {tool.get('name')}")
                    for p in tool.get("parameters") or []:
                        lbl = p.get("label")
                        lbl = lbl.get("zh_Hans") if isinstance(lbl, dict) else lbl
                        print(
                            f"      param name={p.get('name')} type={p.get('type')} form={p.get('form')} required={p.get('required')} default={p.get('default')} | {lbl}"
                        )

    print("\n━━━ 知识库 datasets ━━━")
    ds = _get(client, "/datasets?page=1&limit=100")
    for d in ds.get("data") or []:
        print(f"  {d.get('name')}  id={d.get('id')}  docs={d.get('document_count')}")
    if not (ds.get("data")):
        print(f"  （无 / 或接口返回：{ds}）")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
