# NexusAI 智能对话助理 🚀

这是一个采用极简科技美学设计的全栈 AI 对话应用。前端使用 **Vue 3 (Vite + Options/Composition API)** 打造出拥有磨砂玻璃质感、流光渐变以及极致流畅动画的界面；后端基于 **Python FastAPI**，原生支持高效异步的 **SSE (Server-Sent Events) 流式文本传输**，并无缝集成 OpenAI 兼容接口，连接到 `longcat-flash-chat` 语言模型。

项目完全支持通过 **GitHub Actions** CI/CD 自动化构建，并以**多阶段容器化 (Docker)** 形式打包发布。

---

## ✨ 核心特性

- 🖥️ **极致美学设计**：采用曜石暗黑背景，冷色霓虹（青、蓝、紫）微光渐变，磨砂玻璃面板 (Glassmorphism Blur) 及拟物化交互。
- ⚡ **SSE 流式响应**：基于 FastAPI 异步 Generator 原生提供打字机式的实时回答体验。
- 🛠️ **模型参数微调**：内置配置抽屉，支持运行时调整随机性温度 (Temperature)、最大生成字数 (Max Tokens) 以及注入自定义角色提示词 (System Prompt)。
- 📝 **Markdown 全面支持**：完美支持 Markdown 文本格式渲染，包括精细的代码块展示与一键复制功能。
- 💾 **历史会话记忆**：基于本地浏览器存储 (LocalStorage)，支持多对话历史的新建、切换、命名与清除。
- 🛑 **随时终止生成**：支持前端 `AbortController` 信号中断，随时控制 AI 停止输出。
- 📦 **完美单服务运行**：支持将 Vue3 编译后的静态 SPA 文件打包并直接由 FastAPI 服务托管，生产环境下只需部署一个 Python 进程即可。
- 🤖 **CI/CD 自动发布**：包含 GitHub Actions 自动化流水线，自动检测构建并打包发布 Docker 镜像至 GitHub Packages Container Registry (GHCR)。

---

## 📂 项目结构

```
d:\dadishu\
├── .github/
│   └── workflows/
│       └── deploy.yml          # GitHub Actions 自动化编译、测试与镜像发布
├── backend/
│   ├── app/
│   │   ├── __init__.py
│   │   ├── main.py             # FastAPI 应用入口、SSE 流控制器、静态文件挂载
│   │   └── config.py           # 环境变量与配置参数加载 (Pydantic-Settings)
│   ├── requirements.txt        # 后端依赖包 (Fastapi, uvicorn, openai)
│   └── static/                 # 前端打包后的 HTML/CSS/JS (仅在编译后产生)
├── frontend/
│   ├── index.html              # Google Fonts 及视口配置
│   ├── package.json            # 前端依赖配置
│   ├── vite.config.js          # Vite 配置文件（内嵌反向代理及输出控制）
│   └── src/
│       ├── main.js             # Vue 初始化
│       ├── App.vue             # 页面主布局与对话生命周期管理
│       ├── assets/
│       │   └── style.css       # 核心设计系统、动画与全局 vanilla CSS
│       └── components/
│           ├── Sidebar.vue     # 对话历史抽屉与用户卡片
│           ├── ChatWindow.vue  # 对话气泡、流式监听、快捷指令卡片
│           └── Settings.vue    # 模型微调参数浮层
├── Dockerfile                  # 生产级多阶段构建 Docker 配置文件
└── README.md                   # 项目使用手册
```

---

## 🛠️ 本地开发指南

### 1. 启动后端 API 服务
首先确保本机安装了 Python 3.11+。
```bash
# 1. 进入项目根目录并创建虚拟环境 (Windows/macOS)
python -m venv venv

# 2. 激活虚拟环境 (Windows PowerShell)
.\venv\Scripts\Activate.ps1
# 或 (macOS/Linux)
source venv/bin/activate

# 3. 安装依赖包
pip install -r backend/requirements.txt

# 4. 以前置环境参数形式直接运行 backend 服务 (进入 backend 目录以使模块相对导入正常工作)
cd backend
python -m uvicorn app.main:app --reload --port 8000
```
运行后，后端服务会开启在 `http://127.0.0.1:8000`。
- API 健康检查：`http://127.0.0.1:8000/api/health`
- 交互式 Swagger API 文档：`http://127.0.0.1:8000/docs`

### 2. 启动前端 Vite 开发服务器
确保本机安装了 Node.js 18+。
```bash
# 1. 打开新命令行终端，进入 frontend 文件夹
cd frontend

# 2. 安装前端依赖
npm install

# 3. 运行本地开发热重载服务器
npm run dev
```
前端服务会运行在 `http://localhost:5173`。Vite 配置中已自动内置 `/api` 代理重定向至本地 `8000` 端口，开发中无需担心任何跨域问题。

---

## 📦 生产模式构建与单服务运行

如果不希望运行两个服务（前端+后端），您可以在本地打包前端，并通过 FastAPI 直接以极高性能的静态资源托管形式启动整个应用。

```bash
# 1. 编译前端
cd frontend
npm run build
# 编译后的文件将自动输出到 backend/static/ 目录下

# 2. 启动 FastAPI
cd ../backend
python -m uvicorn app.main:app --port 8000 --host 0.0.0.0
```
现在，直接用浏览器访问 `http://localhost:8000` 即可完全脱离 Node 开发服务器使用全栈应用！

---

## 🐳 Docker 生产级托管

利用根目录下的 `Dockerfile`，只需一行命令即可构建出体积小、安全性高、在任何云服务器上即装即用的应用镜像。

```bash
# 1. 构建 Docker 镜像
docker build -t nexusai:latest .

# 2. 运行容器
docker run -d -p 8000:8000 \
  -e APP_OPENAI_API_KEY="你的API_KEY" \
  --name nexus-assistant nexusai:latest
```

---

## ⚙️ GitHub Actions CI/CD 部署细节

当您将代码推送 (Push) 到关联的 GitHub 仓库的 `main` 或 `master` 分支时，`.github/workflows/deploy.yml` 管道会自动触发：

1. **`build-and-test` 阶段**：
   - 检出代码并拉取 Node 与 Python 环境。
   - 分别安装前后端依赖。
   - 预编译前端 Vue 项目并校验后端 Python 语法编译，若有任何报错将自动熔断，确保主干分支代码百分之百健康。

2. **`build-and-push-image` 阶段**：
   - 依赖测试通过后启动。
   - 登录 GitHub 官方容器镜像仓库 (`ghcr.io`)。
   - 使用 Docker Buildx 开启多阶段高并发缓存构建，在最短时间内将全栈项目打包为高压缩比镜像。
   - 打上 `latest` 以及对应的 `Git Commit SHA` 版本标签并推送到云端库中，等待您的服务器拉取部署。
