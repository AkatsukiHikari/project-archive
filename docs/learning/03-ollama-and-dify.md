# 03 - Ollama 与 Dify 配置指南

## 整体启动顺序

```
1. docker-compose up -d         # 启动所有服务
2. 拉取 Ollama 模型              # 下载 LLM 和 Embedding 模型
3. 配置 Dify                    # 初始化 Dify，连接 Ollama
4. 创建知识库                    # 上传档案文档，让 Dify 向量化
5. 创建应用 + 获取 API Key       # 供 SAMS 后端调用
```

---

## 第一步：启动所有服务

```bash
cd /path/to/project-archive
docker-compose up -d
```

验证各服务状态：

```bash
docker-compose ps
```

Dify 管理后台地址：`http://localhost:8080`  
Ollama API 地址：`http://localhost:11434`

---

## 第二步：拉取 Ollama 模型

Ollama 容器启动后，进入容器拉取模型（或直接调用 API）：

```bash
# 方法一：进入容器操作
docker exec -it sams-ollama ollama pull qwen2.5:7b
docker exec -it sams-ollama ollama pull nomic-embed-text

# 方法二：通过 HTTP API（等效）
curl http://localhost:11434/api/pull -d '{"name": "qwen2.5:7b"}'
curl http://localhost:11434/api/pull -d '{"name": "nomic-embed-text"}'
```

> **注意**：qwen2.5:7b 约 4.7GB，nomic-embed-text 约 274MB，首次下载需要等待。

验证模型是否就绪：

```bash
curl http://localhost:11434/api/tags
# 应该看到 qwen2.5:7b 和 nomic-embed-text 在列表里
```

快速测试对话：

```bash
curl http://localhost:11434/api/generate -d '{
  "model": "qwen2.5:7b",
  "prompt": "你好，请介绍一下档案管理的基本概念",
  "stream": false
}'
```

---

## 第三步：配置 Dify

### 3.1 初始化管理员账号

访问 `http://localhost:8080`，首次进入会要求设置管理员邮箱和密码。

### 3.2 连接 Ollama（设置模型提供商）

进入 **设置 → 模型提供商 → Ollama**，填入：

| 字段 | 值 |
|------|----|
| 基础 URL | `http://ollama:11434`（Docker 内网地址，不是 localhost） |

> **关键**：在 Docker 网络内，服务间通信用容器名，不用 `localhost`。  
> Dify 容器访问 Ollama 容器 → `http://ollama:11434`  
> 你的浏览器访问 Ollama → `http://localhost:11434`

添加**对话模型**：
- 模型名称：`qwen2.5:7b`
- 类型：LLM

添加 **Embedding 模型**：
- 模型名称：`nomic-embed-text`
- 类型：Text Embedding

### 3.3 设置系统默认模型

进入 **设置 → 模型 → 系统模型设置**：
- 推理模型：`qwen2.5:7b`
- Embedding 模型：`nomic-embed-text`
- Rerank 模型：暂时不设置

---

## 第四步：创建档案知识库

### 4.1 新建知识库

进入 **知识库 → 创建知识库**：

- 名称：`SAMS档案知识库`
- 描述：`包含已归档的政府档案文件`

### 4.2 上传档案文档

支持格式：PDF、Word、TXT、Markdown、HTML

上传后 Dify 会自动：
1. 提取文本（PDF 使用 OCR）
2. 按配置切块
3. 调用 nomic-embed-text 生成向量
4. 存入 pgvector

### 4.3 配置切块策略（重要）

进入知识库设置 → 切块设置：

```
切块方式：按段落
最大 Token 数：500
重叠 Token 数：50
```

**档案文件推荐策略**：

| 文件类型 | 建议切块大小 | 原因 |
|---------|------------|------|
| 批复/通知 | 300-500 Token | 文件短，保持完整段落 |
| 法规/条例 | 500-800 Token | 按条款切，保持语义完整 |
| 长篇报告 | 500-600 Token | 避免单块信息过多 |

### 4.4 测试检索效果

在知识库页面有"检索测试"功能，输入问题查看返回的片段和相似度分数：

- 分数 > 0.8：很好
- 分数 0.6-0.8：一般，可优化切块
- 分数 < 0.6：较差，检查文档质量或调整切块策略

---

## 第五步：创建 Dify 应用并获取 API Key

### 5.1 创建应用

进入 **工作室 → 创建应用 → 对话助手**：

- 应用名称：`SAMS档案智能助手`
- 编排模式：`Chatflow`（推荐，支持更复杂的 RAG 流程）

### 5.2 配置知识库检索

在 Chatflow 中添加**知识检索**节点：

- 选择刚创建的 `SAMS档案知识库`
- 检索策略：`混合检索`（向量 + 关键词，效果最好）
- Top K：5（返回最相关的5个片段）
- Score 阈值：0.5（低于此分数的结果不返回）

### 5.3 配置 Prompt

在 LLM 节点设置系统提示词：

```
你是SAMS智能档案助手，专门帮助工作人员查询和理解档案内容。

规则：
1. 只基于提供的档案内容回答，不要编造信息
2. 如果档案中没有相关内容，请明确说明"档案中未找到相关信息"
3. 回答要简洁准确，适合档案工作人员理解
4. 如有引用，请注明来源文件名

档案内容：
{{#context#}}
```

### 5.4 获取 API Key

应用发布后，进入 **API 访问 → API Key**，复制 Key。

将此 Key 填入 SAMS 的 `.env` 文件：

```env
DIFY_BASE_URL=http://localhost:8080/v1
DIFY_API_KEY=app-xxxxxxxxxxxxxxxxxx
```

---

## 常见问题

### Dify 连不上 Ollama

检查：
```bash
# 在 dify-api 容器内测试连通性
docker exec -it sams-dify-api curl http://ollama:11434/api/tags
```

如果失败，检查 docker-compose 网络，确保两个容器在同一网络。

### 向量化速度慢

Embedding 是 CPU 密集操作，正常速度约 50-200 页/分钟（取决于硬件）。首次导入档案文档建议在非业务时间进行。

### 模型回答乱说

调整知识库的 Score 阈值（提高到 0.6-0.7），避免低质量片段进入上下文。同时检查 Prompt 中是否明确要求"只基于档案内容回答"。

---

## 下一步

`04-fastapi-proxy.md` — 如何在 FastAPI 中实现 Dify API 的代理层（含认证、审计、流式 SSE）
