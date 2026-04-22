from pydantic_settings import BaseSettings
from pydantic import Field
from pathlib import Path

THIS_FILE = Path(__file__).resolve()
APP_DIR   = THIS_FILE.parent
ROOT_DIR  = APP_DIR.parent
ENV_FILE  = ROOT_DIR / ".env"


class Settings(BaseSettings):
    groq_api_key: str = Field(..., env="GROQ_API_KEY")
    groq_api_key_2: str = Field("", env="GROQ_API_KEY_2")
    groq_model_extract:  str = Field("meta-llama/llama-4-scout-17b-16e-instruct", env="GROQ_MODEL_EXTRACT")
    groq_model_merge:    str = Field("llama-3.1-8b-instant",                      env="GROQ_MODEL_MERGE")
    groq_model_generate: str = Field("llama-3.3-70b-versatile",                   env="GROQ_MODEL_GENERATE")

    app_env:  str = Field("development", env="APP_ENV")
    app_host: str = Field("0.0.0.0",     env="APP_HOST")
    app_port: int = Field(8000,          env="APP_PORT")

    max_file_size_mb: int = Field(50,   env="MAX_FILE_SIZE_MB")
    job_ttl_seconds:  int = Field(3600, env="JOB_TTL_SECONDS")

    class Config:
        env_file = str(ENV_FILE)
        env_file_encoding = "utf-8"
        extra = "ignore"

    @property
    def upload_dir(self) -> Path:
        return ROOT_DIR / "uploads"

    @property
    def output_dir(self) -> Path:
        return ROOT_DIR / "outputs"

    def ensure_dirs(self):
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.output_dir.mkdir(parents=True, exist_ok=True)
        (ROOT_DIR / "logs").mkdir(parents=True, exist_ok=True)


settings = Settings()
settings.ensure_dirs()