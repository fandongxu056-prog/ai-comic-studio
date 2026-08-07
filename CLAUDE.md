# CLAUDE.md — AI 漫剧创作平台项目指引

## 项目概述

AI 漫剧创作平台是一个浏览器端 SaaS，覆盖从剧本到成片的完整 AI 漫剧创作流程。默认 16:9 横屏。

## 架构

```
四阶段管线（Workflow 编排 + Multi-Agent 创意阶段 + Pipeline 制作阶段）
Stage 1 (Multi-Agent): 剧本 → Stage 2 (Multi-Agent): 资产 → Stage 3 (Multi-Agent): 分镜 → Stage 4 (Pipeline): 制作
```

## 技术栈

- 后端: Python 3.12 + FastAPI + LangGraph + Celery
- 前端: React 19 + TypeScript + Vite + Tailwind CSS 4 + shadcn/ui
- 数据库: PostgreSQL + Redis + MinIO
- 部署: Docker Compose

## 目录结构

```
backend/app/
  api/v1/       — REST API 端点（projects, scripts, assets, storyboards, productions）
  models/       — SQLAlchemy ORM 模型
  schemas/      — Pydantic 请求/响应 Schema
  agents/       — LangGraph Agent 定义（stage1-4）
  contracts/    — 跨阶段连续性契约校验
  services/     — 业务逻辑层
  tasks/        — Celery 异步任务

frontend/src/
  app/          — React Router 路由页面
  components/   — UI 组件（ui/, script/, asset/, storyboard/, production/）
  stores/       — Zustand 状态管理
  services/     — API 客户端

docs/
  schema-design.md                  — 四阶段 JSON Schema 定义
  agent-collaboration-protocol.md   — Multi-Agent 协作协议与品控体系
```

## 关键设计文档

所有编码决策需参考:
- `docs/schema-design.md` — 数据契约的权威来源
- `docs/agent-collaboration-protocol.md` — Agent 协作规范和 QC-5 品控标准

## 开发约定

### Python
- 类型注解: 所有函数参数和返回值必须标注类型
- Pydantic v2: 使用 `model_validate` 而非 `parse_obj`
- SQLAlchemy 2.0: 使用 async session + `select()` 风格
- Agent: 每个 Agent 继承 `agents/base.py` 中的 `BaseAgent`

### TypeScript
- 类型: 严格模式，禁止 `any`
- API 类型: 从 OpenAPI 自动生成（`services/generated/`）
- 状态: Zustand store 按 Stage 拆分，不跨 Stage 共享

### 通用
- ID 格式: 遵循 `docs/schema-design.md` 中的结构化 ID 规范
- 错误处理: 后端返回统一的 `ErrorResponse` Schema
- 流式响应: Agent 过程使用 SSE 推送
