-- 更新chunks表，添加JSON格式的向量字段
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS embedding_json JSONB;

-- 创建索引以提高JSON查询性能
CREATE INDEX IF NOT EXISTS idx_chunks_embedding_json ON chunks USING gin(embedding_json);

-- 添加优先级字段（用于三级知识库）
ALTER TABLE chunks ADD COLUMN IF NOT EXISTS priority INTEGER DEFAULT 2;

-- 创建优先级索引
CREATE INDEX IF NOT EXISTS idx_chunks_priority ON chunks(priority);

-- 添加注释
COMMENT ON COLUMN chunks.embedding_json IS '向量embedding（JSON格式）';
COMMENT ON COLUMN chunks.priority IS '知识库优先级：1=国内口径，2=国际基准，3=区域疫情';
