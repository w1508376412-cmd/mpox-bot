# 猴痘知识问答机器人 🦠

基于RAG（检索增强生成）技术的猴痘/mpox健康科普问答系统，使用WHO、中国疾控中心、CDC等权威来源的知识。

## 特性

- ✅ **权威来源**：基于WHO、中国疾控中心、CDC等权威机构的资料
- ✅ **RAG架构**：使用向量检索而非直接训练，确保信息准确性
- ✅ **安全分诊**：自动识别高风险症状，提供就医建议
- ✅ **地区适配**：支持中国、美国、全球不同地区的政策和就医指导
- ✅ **医疗免责**：明确说明不能替代医生诊断

## 技术栈

- **后端**：Python 3.9+, FastAPI
- **向量数据库**：PostgreSQL + pgvector
- **大模型**：OpenAI GPT-4o-mini
- **Embedding**：OpenAI text-embedding-3-small
- **前端**：原生HTML/CSS/JavaScript

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd mpox-bot

# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 文件，填入你的 OpenAI API Key
```

### 2. 数据库设置

```bash
# 安装 PostgreSQL 和 pgvector
# macOS
brew install postgresql pgvector

# 启动 PostgreSQL
brew services start postgresql

# 创建数据库
createdb mpox_bot

# 初始化表结构
psql mpox_bot < init_db.sql
```

### 3. 数据采集和处理

```bash
cd backend

# 抓取权威数据源
python crawler.py

# 处理数据并生成向量
python process_data.py
```

### 4. 启动服务

```bash
# 启动后端API
cd backend
python main.py

# 访问前端页面
# 打开浏览器访问: http://localhost:8000
```

## 项目结构

```
mpox-bot/
├── backend/              # 后端代码
│   ├── main.py          # FastAPI主程序
│   ├── config.py        # 配置管理
│   ├── schemas.py       # 数据模型
│   ├── crawler.py       # 数据采集
│   ├── chunker.py       # 文档切片
│   ├── embedder.py      # 向量生成
│   ├── retriever.py     # 检索逻辑
│   ├── generator.py     # 回答生成
│   ├── safety.py        # 安全分诊
│   └── process_data.py  # 数据处理脚本
├── data/                # 数据目录
│   ├── raw/            # 原始数据
│   └── processed/      # 处理后的数据
├── prompts/            # 提示词模板
│   └── system_prompt.txt
├── eval/               # 测试评估
│   └── test_questions.json
├── frontend/           # 前端页面
│   └── index.html
├── init_db.sql        # 数据库初始化脚本
├── requirements.txt   # Python依赖
├── .env.example       # 环境变量模板
└── README.md          # 项目文档
```

## API文档

### POST /chat

问答接口

**请求体：**
```json
{
  "question": "猴痘是怎么传播的？",
  "region": "中国"
}
```

**响应：**
```json
{
  "answer": "根据WHO和中国疾控中心的资料...",
  "risk_type": "general",
  "sources": [
    {
      "source": "WHO",
      "url": "https://www.who.int/...",
      "publish_date": "2024-08-01"
    }
  ],
  "disclaimer": "本机器人仅提供猴痘/mpox健康科普信息..."
}
```

**风险类型：**
- `general`: 一般科普问题
- `symptom_risk`: 症状相关，需要就医建议
- `high_risk`: 高风险症状，需要紧急就医
- `policy`: 政策和就医流程咨询

## 数据源

| 来源 | 用途 | 更新频率 |
|------|------|----------|
| WHO Mpox Fact Sheet | 全球通用科普、症状、传播、预防 | 定期 |
| WHO Mpox Q&A | 常见问答、性接触、旅行、居家隔离 | 定期 |
| 中国疾控中心 | 中国语境下的防控、就医、密接管理 | 定期 |
| CDC | 症状、预防、医疗机构指导、检测建议 | 定期 |

## 安全规则

1. **不做医学诊断**：明确说明无法在线诊断是否感染
2. **症状分诊**：自动识别高风险症状，建议就医
3. **地区适配**：根据用户地区提供相应的就医指导
4. **来源追溯**：每个结论都标注权威来源
5. **医疗免责**：明确告知不能替代医生诊断

## 测试

```bash
# 运行测试集
cd eval
python run_eval.py
```

测试集包含20个典型问题，覆盖：
- 基础科普
- 传播途径
- 症状识别
- 暴露处理
- 高风险情况
- 政策咨询

## 更新知识库

```bash
# 重新抓取数据源
cd backend
python crawler.py

# 重新处理并更新向量
python process_data.py
```

建议每周或每月更新一次，确保信息时效性。

## 注意事项

1. **API费用**：使用OpenAI API会产生费用，建议设置使用限额
2. **数据隐私**：不要在问题中包含个人隐私信息
3. **医疗免责**：本系统仅供科普，不能替代医生诊断
4. **地区差异**：不同地区的政策和就医流程可能不同

## 许可证

MIT License

## 联系方式

如有问题或建议，请提交Issue。

---

**医疗免责声明**：本机器人仅提供猴痘/mpox健康科普信息，不能替代医生诊断或治疗。如出现新发或原因不明皮疹、发热、淋巴结肿大，或有可疑接触史，请咨询医疗机构或当地疾控部门。
