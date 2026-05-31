-- 数据库初始化脚本
-- 创建猴痘知识问答机器人所需的表结构

-- 启用pgvector扩展
CREATE EXTENSION IF NOT EXISTS vector;

-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    source_primary TEXT,
    source_department TEXT,
    source_orgs TEXT[],
    url TEXT NOT NULL,
    url_status TEXT DEFAULT 'present',
    url_missing_reason TEXT DEFAULT '',
    publish_date DATE NOT NULL,
    date_source TEXT DEFAULT 'raw_publish_date',
    date_confidence TEXT DEFAULT 'high',
    region TEXT NOT NULL,
    original_file TEXT,
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识片段表
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    content_preview TEXT,
    content_hash TEXT,
    section_title TEXT,
    chunk_index INTEGER,
    start_char INTEGER,
    end_char INTEGER,
    topic TEXT[] NOT NULL,
    embedding vector(1024),  -- 阿里百炼 text-embedding-v4 维度
    embedding_json JSONB,
    embedding_model TEXT DEFAULT 'text-embedding-v4',
    source TEXT NOT NULL,
    source_primary TEXT,
    source_department TEXT,
    url TEXT NOT NULL,
    publish_date DATE NOT NULL,
    date_confidence TEXT DEFAULT 'high',
    region TEXT NOT NULL,
    priority INTEGER DEFAULT 2,
    quality_score NUMERIC(3,2) DEFAULT 1.00,
    quality_warnings TEXT[] DEFAULT '{}',
    contains_mpox_keyword BOOLEAN DEFAULT true,
    is_footer_like BOOLEAN DEFAULT false,
    is_suspected_irrelevant BOOLEAN DEFAULT false,
    language TEXT DEFAULT 'zh',
    is_active BOOLEAN DEFAULT true,
    version TEXT DEFAULT '1.0',
    processed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建向量相似度搜索索引
CREATE INDEX IF NOT EXISTS chunks_embedding_idx ON chunks
USING ivfflat (embedding vector_cosine_ops)
WITH (lists = 100);

-- 创建其他常用索引
CREATE INDEX IF NOT EXISTS chunks_region_idx ON chunks(region);
CREATE INDEX IF NOT EXISTS chunks_is_active_idx ON chunks(is_active);
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);
CREATE INDEX IF NOT EXISTS chunks_content_hash_idx ON chunks(content_hash);
CREATE INDEX IF NOT EXISTS chunks_quality_score_idx ON chunks(quality_score);

-- 创建更新时间触发器
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_documents_updated_at BEFORE UPDATE ON documents
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- 插入示例文档（可选）
COMMENT ON TABLE documents IS '存储原始文档的元数据';
COMMENT ON TABLE chunks IS '存储文档切片和向量';
COMMENT ON COLUMN chunks.embedding IS '文本向量，使用阿里百炼 text-embedding-v4 生成';
COMMENT ON COLUMN chunks.quality_score IS '片段质量评分，越高越适合检索生成';
COMMENT ON COLUMN chunks.quality_warnings IS '片段质量问题标签';
COMMENT ON COLUMN chunks.is_active IS '标记片段是否有效，用于版本管理';
