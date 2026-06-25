"""
AI 能力 service 集合

每个能力一个独立 service 模块；统一通过 ``dispatch(code, ...)`` 入口调用。
设计稿 §5.3：dispatch 不直接调子 Workflow，而是把数据准备好返回；子 Workflow 是
Dify 内部的 LLM 包装层（A' 方案的"答案格式化"由子 Workflow 的 LLM 节点完成）。

8 个能力（按肉眼可见优先级）：
  qa / search / summary / kb_manage / relate / catalog / attach / draft
  fournat 当前优先级低（实装在 fournat_service 但 dispatch 暂时返回 not_implemented）
"""

from app.modules.ai.services.capabilities.dispatcher import (dispatch,
                                                             get_capability)

__all__ = ["dispatch", "get_capability"]
