# SubAutoTrans

自动字幕翻译服务 - 使用 LLM 自动翻译 MKV 视频文件或独立字幕文件中的字幕。

## 功能特性

- **多格式支持**: 支持 MKV 视频文件、SRT 和 ASS 字幕文件
- **多 LLM 支持**: OpenAI、Claude、DeepSeek、GLM 等多种大语言模型
- **批量处理**: 支持整个目录批量添加翻译任务
- **目录监控**: 自动监控指定目录，新文件自动创建翻译任务
- **智能跳过**: 自动检测已翻译的文件，避免重复翻译
- **双语字幕**: 支持生成双语字幕（原文 + 译文）
- **多种输出**: 支持输出为 MKV（内嵌字幕）、SRT 或 ASS 格式
- **实时进度**: WebSocket 实时推送翻译进度
- **SMB 支持**: 支持跨设备文件系统（如 NAS）

## 系统要求

- FFmpeg
- MKVToolNix (mkvmerge)
- Python 3.12+ 或 Docker

## 快速开始

### Docker 部署（推荐）

1. **克隆项目**
```bash
git clone https://github.com/yourname/SubAutoTrans.git
cd SubAutoTrans
```

2. **配置环境变量**
```bash
cp .env.example .env
# 编辑 .env 文件，填入你的 API Key
```

3. **启动服务**
```bash
docker-compose up -d --build
```

4. **访问界面**
```
http://localhost:8000
```

### 手动部署

#### 安装系统依赖

```bash
# macOS
brew install ffmpeg mkvtoolnix

# Ubuntu/Debian
sudo apt install ffmpeg mkvtoolnix

# Windows
# 从官网下载安装 FFmpeg 和 MKVToolNix
```

#### 后端

```bash
cd backend

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 安装依赖
pip install -r requirements.txt

# 配置环境变量（或创建 .env 文件）
export OPENAI_API_KEY=sk-your-key

# 启动服务
python run.py
```

#### 前端

```bash
cd frontend

# 安装依赖
npm install

# 开发模式
npm run dev

# 或构建生产版本
npm run build
```

## 配置说明

### 环境变量

| 变量 | 说明 | 默认值 |
|------|------|--------|
| `OPENAI_API_KEY` | OpenAI API Key | - |
| `OPENAI_MODEL` | OpenAI 模型 | gpt-4o-mini |
| `OPENAI_BASE_URL` | OpenAI API 地址 | - |
| `ANTHROPIC_API_KEY` | Claude API Key | - |
| `CLAUDE_MODEL` | Claude 模型 | claude-sonnet-4-20250514 |
| `DEEPSEEK_API_KEY` | DeepSeek API Key | - |
| `DEEPSEEK_MODEL` | DeepSeek 模型 | deepseek-chat |
| `GLM_API_KEY` | GLM API Key | - |
| `GLM_MODEL` | GLM 模型 | glm-4-flash |
| `SOURCE_LANGUAGE` | 源语言 | auto |
| `TARGET_LANGUAGE` | 目标语言 | Chinese |
| `DEFAULT_LLM` | 默认 LLM 提供商 | openai |
| `MAX_CONCURRENT_TASKS` | 最大并发任务数 | 2 |
| `BILINGUAL_OUTPUT` | 是否输出双语字幕 | false |
| `SUBTITLE_OUTPUT_FORMAT` | 输出格式 (mkv/srt/ass) | mkv |
| `OVERWRITE_MKV` | 是否覆盖原 MKV | false |

### Docker 挂载媒体目录

编辑 `docker-compose.yml`：

```yaml
volumes:
  - ./data:/app/data
  - /path/to/your/media:/media:ro  # 添加媒体目录
```

## 使用说明

### 添加翻译任务

1. 进入 **Files** 页面
2. 浏览并选择 MKV/SRT/ASS 文件或目录
3. 选择目标语言和 LLM 提供商
4. 点击 **Create Task**

### 目录监控

1. 进入 **Watchers** 页面
2. 点击 **Add Watcher**
3. 选择要监控的目录
4. 设置目标语言和 LLM 提供商
5. 点击 **Create Watcher**

监控功能会：
- 启动时扫描目录中的现有文件
- 实时监控新增文件（包括子目录）
- 自动跳过已翻译的文件

### 任务管理

- **Tasks** 页面查看所有任务状态和进度
- 支持暂停、重试、删除单个或批量任务
- 支持按状态筛选和分页浏览

## API 接口

服务启动后访问 `http://localhost:8000/docs` 查看完整 API 文档。

### 主要接口

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | /api/tasks | 获取任务列表（分页） |
| POST | /api/tasks | 创建单个任务 |
| POST | /api/tasks/directory | 批量创建任务 |
| DELETE | /api/tasks/{id} | 删除任务 |
| POST | /api/tasks/{id}/retry | 重试任务 |
| GET | /api/watchers | 获取监控列表 |
| POST | /api/watchers | 创建监控 |
| WS | /ws/progress | WebSocket 进度推送 |

## 智能跳过机制

系统会自动跳过以下情况：

1. **数据库已记录**: 文件已成功翻译过
2. **任务已存在**: 相同文件+语言的任务正在处理中
3. **MKV 已有目标语言**: MKV 文件中已包含目标语言字幕轨
4. **输出文件已存在**: 对应的翻译输出文件已存在
5. **文件名包含语言标记**: 如 `.zh-Hans.srt`、`.translated.mkv`

## 项目结构

```
SubAutoTrans/
├── backend/                 # Python 后端
│   ├── app/
│   │   ├── routers/        # API 路由
│   │   ├── services/       # 业务逻辑
│   │   ├── models/         # 数据模型
│   │   ├── llm/            # LLM 适配器
│   │   └── main.py         # 应用入口
│   ├── requirements.txt
│   └── run.py
├── frontend/               # React 前端
│   ├── src/
│   │   ├── pages/         # 页面组件
│   │   ├── components/    # 通用组件
│   │   └── api/           # API 客户端
│   └── package.json
├── Dockerfile
├── docker-compose.yml
└── README.md
```

## 常见问题

### Q: 翻译失败提示 Authentication Fails
A: 检查对应 LLM 的 API Key 是否正确配置。

### Q: 跨设备链接错误 (Cross-device link)
A: 系统已处理此问题，支持 SMB/NFS 等网络文件系统。

### Q: 字幕编码错误
A: 系统自动检测文件编码（UTF-8/UTF-16 等），无需手动处理。

### Q: 如何更换 LLM 提供商
A: 在 Settings 页面修改默认 LLM，或在创建任务时选择。

## License

GPL-3.0
