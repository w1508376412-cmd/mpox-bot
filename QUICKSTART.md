# 快速开始指南

## 🚀 5分钟快速启动

### 前置要求

1. **Python 3.9+**
2. **PostgreSQL** (带pgvector扩展)
3. **OpenAI API Key**

### 快速启动步骤

```bash
# 1. 进入项目目录
cd mpox-bot

# 2. 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 OpenAI API Key

# 3. 一键启动（自动安装依赖、初始化数据库、抓取数据）
./start.sh
```

访问 http://localhost:8000 即可使用！

---

## 📋 详细步骤

### 步骤1：安装依赖

```bash
pip install -r requirements.txt
```

### 步骤2：配置环境变量

```bash
cp .env.example .env
```

编辑 `.env` 文件：
```env
OPENAI_API_KEY=sk-your-api-key-here
OPENAI_MODEL=gpt-4o-mini
EMBEDDING_MODEL=text-embedding-3-small
DATABASE_URL=postgresql://postgres:password@localhost:5432/mpox_bot
```

### 步骤3：初始化数据库

```bash
# 创建数据库
createdb mpox_bot

# 初始化表结构
psql mpox_bot < init_db.sql
```

### 步骤4：抓取和处理数据

```bash
cd backend

# 抓取权威数据源（WHO、中国疾控、CDC）
python crawler.py

# 处理数据并生成向量
python process_data.py
```

### 步骤5：启动服务

```bash
# 启动后端API
python main.py
```

访问：
- **前端页面**：http://localhost:8000
- **API文档**：http://localhost:8000/docs
- **健康检查**：http://localhost:8000/health

---

## 🐳 使用Docker启动

```bash
# 1. 配置环境变量
cp .env.example .env
# 编辑 .env 填入 API Key

# 2. 启动服务
docker-compose up -d

# 3. 查看日志
docker-compose logs -f backend

# 4. 停止服务
docker-compose down
```

---

## 🧪 测试

```bash
# 运行测试集
cd eval
python run_eval.py

# 限制测试数量
python run_eval.py --limit 5

# 指定测试地区
python run_eval.py --region 美国
```

---

## 📝 使用示例

### API调用示例

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "question": "猴痘是怎么传播的？",
    "region": "中国"
  }'
```

### Python调用示例

```python
import requests

response = requests.post(
    "http://localhost:8000/chat",
    json={
        "question": "猴痘是怎么传播的？",
        "region": "中国"
    }
)

result = response.json()
print(result["answer"])
print(result["sources"])
```

---

## 🔄 更新知识库

```bash
cd backend

# 重新抓取最新数据
python crawler.py

# 重新处理并更新向量
python process_data.py

# 运行测试验证
cd ../eval
python run_eval.py
```

建议每周或每月更新一次。

---

## ❓ 常见问题

### Q1: 数据库连接失败？

**A:** 检查PostgreSQL是否启动：
```bash
# macOS
brew services start postgresql

# Linux
sudo systemctl start postgresql
```

### Q2: OpenAI API调用失败？

**A:** 检查：
1. API Key是否正确配置在 `.env` 文件中
2. API Key是否有效且有余额
3. 网络是否能访问OpenAI API

### Q3: 向量检索没有结果？

**A:** 确保已经运行数据处理：
```bash
cd backend
python process_data.py
```

### Q4: 如何添加新的数据源？

**A:** 编辑 `backend/crawler.py`，在 `SOURCES` 列表中添加新的数据源配置。

---

## 📊 项目结构

```
mpox-bot/
├── backend/              # 后端代码
│   ├── main.py          # FastAPI主程序
│   ├── crawler.py       # 数据采集
│   ├── embedder.py      # 向量生成
│   ├── retriever.py     # 检索逻辑
│   ├── generator.py     # 回答生成
│   └── safety.py        # 安全分诊
├── frontend/            # 前端页面
│   └── index.html
├── prompts/             # 提示词模板
├── eval/                # 测试评估
├── data/                # 数据目录
├── init_db.sql         # 数据库初始化
├── start.sh            # 快速启动脚本
└── README.md           # 项目文档
```

---

## 🎯 核心特性

✅ **RAG架构**：基于向量检索，不训练模型
✅ **权威来源**：WHO、中国疾控、CDC等官方资料
✅ **安全分诊**：自动识别高风险症状
✅ **地区适配**：支持中国、美国、全球
✅ **医疗免责**：明确说明不能替代医生诊断

---

## 📞 获取帮助

- 查看详细文档：`README.md`
- 查看项目总结：`PROJECT_SUMMARY.md`
- 查看API文档：http://localhost:8000/docs

---

**医疗免责声明**：本机器人仅提供猴痘/mpox健康科普信息，不能替代医生诊断或治疗。
