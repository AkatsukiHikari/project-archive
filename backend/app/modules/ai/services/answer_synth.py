"""
答案合成器（无 Dify 时的兜底）

设计稿 §3.2 第 4 条："每个 AI 输出都带引用"。
当 Dify 未配置（DIFY_API_KEY 为空）或调用失败，本服务直接基于 retrieval_service 的命中
合成一份"引用拼接式"答案，让 demo 不依赖外部服务也能走完一次问答闭环。

这不是"AI 回答"，只是把命中 chunk 的标题 + 片段顺序拼出来，前端引用 chip 仍然有效。
风格遵循设计稿 §3.2：无证据则拒答；不编造、不超出引用范围。
"""

from __future__ import annotations

from app.modules.ai.services.retrieval_service import RetrievedChunk

_REFUSE_NO_EVIDENCE = (
    "未在知识库中找到与此问题相关的档案或业务规则。"
    "请尝试换个表述、补充时间/全宗号等条件，或前往档案检索页直接查询。"
)


def synthesize_answer(*, query: str, chunks: list[RetrievedChunk]) -> str:
    """从 retrieved chunks 拼装一段引用式回答。"""
    if not chunks:
        return _REFUSE_NO_EVIDENCE

    rules = [c for c in chunks if c.source_type == "rule"]
    metas = [c for c in chunks if c.source_type == "meta"]

    lines: list[str] = []

    if rules:
        if len(rules) == 1:
            r = rules[0]
            lines.append(f"根据《{r.title}》：")
            lines.append(r.snippet)
        else:
            lines.append("根据知识库检索到的相关规则：")
            for idx, r in enumerate(rules[:3], start=1):
                lines.append(f"\n{idx}. **{r.title}**")
                lines.append(f"   {r.snippet}")

    if metas:
        if rules:
            lines.append("\n\n相关档案：")
        else:
            lines.append("找到以下相关档案：")
        for idx, m in enumerate(metas[:5], start=1):
            line = f"{idx}. {m.title}"
            if m.snippet:
                line += f"（{m.snippet}）"
            lines.append(line)

    lines.append(
        "\n\n— 本答案由知识库检索结果直接拼装，未经大模型重述。点击下方引用可查看完整出处。"
    )
    return "\n".join(lines)
