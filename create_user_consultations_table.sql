-- 创建用户咨询记录表
CREATE TABLE IF NOT EXISTS user_consultations (
    id SERIAL PRIMARY KEY,
    user_name TEXT NOT NULL,
    antiviral_id TEXT NOT NULL,
    question TEXT NOT NULL,
    answer TEXT NOT NULL,
    risk_type TEXT NOT NULL,
    region TEXT DEFAULT '中国',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 创建索引以提高查询性能
CREATE INDEX IF NOT EXISTS idx_user_consultations_antiviral_id ON user_consultations(antiviral_id);
CREATE INDEX IF NOT EXISTS idx_user_consultations_created_at ON user_consultations(created_at);
CREATE INDEX IF NOT EXISTS idx_user_consultations_user_name ON user_consultations(user_name);

-- 添加注释
COMMENT ON TABLE user_consultations IS '用户咨询记录表，存储用户姓名、抗病毒编号和咨询内容';
COMMENT ON COLUMN user_consultations.user_name IS '用户姓名';
COMMENT ON COLUMN user_consultations.antiviral_id IS '抗病毒编号';
COMMENT ON COLUMN user_consultations.question IS '用户提问';
COMMENT ON COLUMN user_consultations.answer IS 'AI回答';
COMMENT ON COLUMN user_consultations.risk_type IS '风险类型';
COMMENT ON COLUMN user_consultations.region IS '地区';
COMMENT ON COLUMN user_consultations.created_at IS '咨询时间';
