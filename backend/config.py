from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    # OpenAI-compatible chat completion config. Defaults target DeepSeek.
    openai_api_key: str
    openai_model: str = "deepseek-v4-flash"
    openai_api_base: str = "https://api.deepseek.com"

    # 阿里百炼配置（用于向量生成）
    alibaba_api_key: str = ""
    alibaba_api_base: str = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    embedding_model: str = "text-embedding-v4"

    # 数据库配置
    database_url: str

    # 服务配置
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    # 默认地区
    default_region: str = "中国"

    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings():
    return Settings()
