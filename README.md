# NovaMind 企业级 AI RAG 知识库系统

## 项目结构

```
06 NovaMind/
├── frontend/               # Vue3 + Vite + TypeScript 前端
│   ├── src/
│   │   ├── api/            # API 封装 (chat.ts, file.ts)
│   │   ├── assets/         # 全局样式
│   │   ├── components/     # 公共组件 (AppLayout)
│   │   ├── composables/    # 可复用逻辑（预留）
│   │   ├── router/         # Vue Router
│   │   ├── stores/         # Pinia Store
│   │   ├── types/          # TypeScript 类型
│   │   ├── utils/          # HTTP 封装
│   │   └── views/          # 页面 chat / upload / files / settings
│   ├── index.html
│   ├── vite.config.ts
│   └── package.json
│
├── backend/                # FastAPI + Python 后端
│   └── app/
│       ├── api/v1/         # 路由 (chat, files)
│       ├── core/           # config, logging, exceptions
│       ├── db/             # 数据库引擎
│       ├── models/         # SQLAlchemy ORM 模型
│       ├── repositories/   # 数据访问层
│       ├── services/       # 业务服务 (LLM, Embedding)
│       ├── schemas/        # Pydantic schemas
│       ├── tools/          # Tool Registry + WeatherTool
│       ├── rag/            # PDF 解析 + 向量检索
│       ├── memory/         # 短期记忆
│       ├── prompts/        # Prompt 模板
│       ├── utils/          # 工具函数
│       └── main.py         # FastAPI 入口
│   ├── requirements.txt
│   ├── Dockerfile
│   └── .env.example
│
└── docker-compose.yml      # PostgreSQL + pgvector + Backend
```

## 快速开始

### 后端

```bash
cd backend
cp .env.example .env
# 编辑 .env 填入 API Key

pip install -r requirements.txt
uvicorn app.main:app --reload
```

### 前端

```bash
cd frontend
npm install
npm run dev
```

### Docker

```bash
docker-compose up -d
```

## 接口文档

启动后访问：http://localhost:8000/docs

python -m uvicorn app.main:app --reload

```
git clone https://github.com/liuyuwen6666/novamind.git
cd novamind
cp .env.example .env
# 编辑 .env 改 VITE_API_BASE_URL=http://你的服务器IP:8000
docker compose up -d

```