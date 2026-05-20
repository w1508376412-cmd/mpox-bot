-- 简化版数据库初始化脚本（不使用pgvector）
-- 创建猴痘知识问答机器人所需的表结构

-- 文档表
CREATE TABLE IF NOT EXISTS documents (
    id TEXT PRIMARY KEY,
    title TEXT NOT NULL,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    publish_date DATE NOT NULL,
    region TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 知识片段表（简化版，不使用向量）
CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    document_id TEXT REFERENCES documents(id) ON DELETE CASCADE,
    content TEXT NOT NULL,
    topic TEXT[] NOT NULL,
    source TEXT NOT NULL,
    url TEXT NOT NULL,
    publish_date DATE NOT NULL,
    region TEXT NOT NULL,
    is_active BOOLEAN DEFAULT true,
    version TEXT DEFAULT '1.0',
    last_checked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建全文搜索索引（替代向量搜索）
CREATE INDEX IF NOT EXISTS chunks_content_idx ON chunks USING gin(to_tsvector('simple', content));
CREATE INDEX IF NOT EXISTS chunks_region_idx ON chunks(region);
CREATE INDEX IF NOT EXISTS chunks_is_active_idx ON chunks(is_active);
CREATE INDEX IF NOT EXISTS chunks_document_id_idx ON chunks(document_id);

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

-- 注释
COMMENT ON TABLE documents IS '存储原始文档的元数据';
COMMENT ON TABLE chunks IS '存储文档切片（简化版，使用全文搜索）';
