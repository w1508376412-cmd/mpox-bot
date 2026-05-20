# 猴痘知识库向量检索系统 - 完整实施指南

## 📋 系统架构

### 三级优先级知识库策略

1. **第一优先级：国内回答口径** (priority=1)
   - 国家疾控局/国家卫健委
   - 中国疾控中心
   - 用于：防控、就医、报告、隔离、科普

2. **第二优先级：国际医学与流行病学基准** (priority=2)
   - WHO + CDC + ECDC
   - 用于：症状、传播、诊断、疫苗、治疗、分支、全球疫情

3. **第三优先级：区域疫情与监测** (priority=3)
   - Africa CDC + UKHSA + CHP
   - 用于：旅行、区域风险、国外疫情、公共卫生措施

---

## 🎯 当前实施状态

### ✅ 已完成
1. 数据库表结构已更新（支持优先级字段）
2. 用户信息登记功能（姓名、抗病毒编号）
3. 基础的文本检索功能
4. 咨询记录保存功能

### 🔄 待实施（向量检索）

由于以下技术限制：
- DeepSeek API 不支持 embedding 功能
- pgvector 在 PostgreSQL 14 上配置复杂

**推荐方案：**
使用 **OpenAI embedding API** 来生成向量，这是最稳定和成熟的方案。

---

## 🚀 完整实施步骤

### 方案A：使用 OpenAI Embedding（推荐）

#### 步骤1：获取 OpenAI API Key

访问 https://platform.openai.com/api-keys 获取 API Key

#### 步骤2：更新 .env 配置

```bash
# 在 .env 文件中添加
OPENAI_API_KEY=sk-your-openai-key-here
OPENAI_EMBEDDING_MODEL=text-embedding-3-small
```

#### 步骤3：安装 pgvector 扩展

```bash
# 方法1：使用预编译版本（推荐）
brew install pgvector

# 方法2：从源码编译
git clone https://github.com/pgvector/pgvector.git
cd pgvector
make
make install  # 可能需要 sudo

# 重启 PostgreSQL
brew services restart postgresql@14
```

#### 步骤4：在数据库中启用 pgvector

```sql
-- 连接到数据库
psql mpox_bot

-- 启用扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 更新 chunks 表，添加向量字段
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding vector(1536);

-- 创建向量索引
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);
```

#### 步骤5：更新 embedder.py

```python
"""向量生成模块 - 使用 OpenAI Embedding API"""
from openai import OpenAI
from typing import List
from config import get_settings

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)

def embed_text(text: str) -> List[float]:
    """生成文本向量"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def embed_batch(texts: List[str]) -> List[List[float]]:
    """批量生成向量"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=texts
    )
    return [item.embedding for item in response.data]
```

#### 步骤6：更新 retriever.py（向量检索）

```python
"""检索模块 - 基于向量相似度和优先级"""
import psycopg
from typing import List, Dict, Any
from embedder import embed_text
from config import get_settings

settings = get_settings()

def get_db_connection():
    return psycopg.connect(settings.database_url, client_encoding='utf8')

def search_chunks(question: str, region: str = "中国", top_k: int = 5):
    """向量检索 + 优先级加权"""
    question_vector = embed_text(question)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                \"\"\"
                SELECT content, source, url, publish_date, region, priority,
                       embedding <-> %s::vector as distance
                FROM chunks
                WHERE is_active = true
                  AND (region = %s OR region = 'global')
                ORDER BY
                    priority ASC,  -- 优先级优先
                    distance ASC   -- 然后按相似度
                LIMIT %s
                \"\"\",
                (question_vector, region, top_k)
            )
            
            rows = cur.fetchall()
            return [{
                "content": row[0],
                "source": row[1],
                "url": row[2],
                "publish_date": row[3],
                "region": row[4],
                "priority": row[5]
            } for row in rows]
```

#### 步骤7：数据采集和向量化

```python
# 运行数据采集脚本
cd backend
python crawler.py  # 抓取网页
python process_data.py  # 生成向量并存入数据库
```

---

### 方案B：混合检索（当前可用）

如果暂时无法使用 OpenAI API，可以使用**增强的文本匹配 + 优先级**：

#### 当前已实现的功能

1. **优先级加权检索**
   - 国内口径（priority=1）权重最高
   - 国际基准（priority=2）权重中等
   - 区域疫情（priority=3）权重较低

2. **关键词匹配**
   - 自动匹配：猴痘、症状、传播、预防、治疗等关键词
   - 用户问题精确匹配

3. **地区过滤**
   - 优先返回用户所在地区的内容
   - 自动包含全球通用内容

#### 使用方法

当前系统已经在使用混合检索，无需额外配置。

---

## 📊 数据源配置

### 已配置的数据源（data_sources.py）

#### 第一优先级：国内口径（3个）
1. 国家卫健委猴痘防控指南
2. 中国疾控中心防控知识问答
3. 中国疾控中心健康防护提示

#### 第二优先级：国际基准（8个）
1. WHO Mpox Fact Sheet
2. WHO Mpox Q&A
3. WHO Mpox Outbreak Updates
4. CDC About Mpox
5. CDC Symptoms
6. CDC Prevention
7. CDC Treatment
8. ECDC Mpox Factsheet

#### 第三优先级：区域疫情（3个）
1. Africa CDC Mpox Information
2. UKHSA Mpox Guidance
3. 香港卫生防护中心猴痘专页

**总计：14个权威数据源**

---

## 🔧 维护和更新

### 定期更新知识库

```bash
# 每周或每月运行一次
cd backend
python crawler.py  # 重新抓取最新数据
python process_data.py  # 更新向量
```

### 查看数据统计

```sql
-- 查看各优先级的数据量
SELECT priority,
       CASE priority
           WHEN 1 THEN '国内口径'
           WHEN 2 THEN '国际基准'
           WHEN 3 THEN '区域疫情'
       END as priority_name,
       COUNT(*) as count
FROM chunks
WHERE is_active = true
GROUP BY priority
ORDER BY priority;

-- 查看各来源的数据量
SELECT source, COUNT(*) as count
FROM chunks
WHERE is_active = true
GROUP BY source
ORDER BY count DESC;
```

---

## 💰 成本估算

### OpenAI Embedding API 费用

- **模型**：text-embedding-3-small
- **价格**：$0.00002 / 1K tokens
- **估算**：
  - 初始化 500 个片段：约 $0.05
  - 每次查询：约 $0.0001
  - 月成本（1000次查询）：约 $0.10

### DeepSeek Chat API 费用

- **模型**：deepseek-chat
- **价格**：约 $0.001 / 1K tokens
- **估算**：
  - 每次问答：约 $0.001
  - 月成本（1000次问答）：约 $1

**总月成本**：约 $1-2（非常经济）

---

## 🎯 下一步行动

### 立即可做
1. ✅ 使用当前的混合检索系统（已可用）
2. ✅ 测试用户信息登记功能
3. ✅ 查看咨询记录

### 短期优化（1-2周）
1. 获取 OpenAI API Key
2. 配置 pgvector 扩展
3. 实施完整的向量检索

### 长期扩展（1-2月）
1. 抓取所有14个数据源
2. 定期更新知识库
3. 添加更多区域数据源

---

## 📞 技术支持

### 常见问题

**Q1: DeepSeek 支持 embedding 吗？**
A: 目前不支持。建议使用 OpenAI embedding API。

**Q2: 必须使用向量检索吗？**
A: 不是必须的。当前的混合检索（文本匹配+优先级）已经能提供良好的效果。

**Q3: 如何添加新的数据源？**
A: 编辑 `backend/data_sources.py`，添加新的数据源配置，然后运行 `crawler.py`。

**Q4: 如何查看系统运行状态？**
A: 访问 http://localhost:8000/health 查看健康状态。

---

## 📝 文件清单

### 核心文件
- `backend/data_sources.py` - 三级数据源配置
- `backend/retriever_v2.py` - 增强检索模块
- `backend/embedder.py` - 向量生成模块
- `update_chunks_table.sql` - 数据库更新脚本

### 配置文件
- `.env` - 环境变量配置
- `backend/config.py` - 配置管理

### 数据库
- `mpox_bot` - 主数据库
- `chunks` 表 - 知识片段（含优先级字段）
- `user_consultations` 表 - 用户咨询记录

---

**最后更新**：2026-05-06
**版本**：v2.0 - 三级知识库 + 向量检索
