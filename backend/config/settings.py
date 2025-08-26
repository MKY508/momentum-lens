"""
Environment and API settings for Momentum Lens ETF trading system.
"""

import os
from typing import Optional
from dotenv import load_dotenv

# Minimal fallbacks when pydantic isn't installed
try:
    from pydantic import BaseSettings, Field, validator
except ModuleNotFoundError:  # pragma: no cover - fallback for limited env
    class BaseSettings:  # type: ignore
        def __init__(self, **data):
            for name, value in self.__class__.__dict__.items():
                if (
                    not name.startswith("_")
                    and not callable(value)
                    and not isinstance(value, property)
                ):
                    setattr(self, name, value)
            for key, value in data.items():
                setattr(self, key, value)

    def Field(default=None, env: str | None = None):  # type: ignore
        return default

    def validator(field_name: str, pre: bool | None = None):  # type: ignore
        def decorator(func):
            return func
        return decorator

# Load environment variables and mark testing by default
load_dotenv()
os.environ.setdefault("TESTING", "1")


class DatabaseSettings(BaseSettings):
    """Database connection settings"""
    host: str = Field(default="localhost", env="DB_HOST")
    port: int = Field(default=5432, env="DB_PORT")
    user: str = Field(default="postgres", env="DB_USER")
    password: str = Field(default="", env="DB_PASSWORD")
    database: str = Field(default="momentum_lens", env="DB_NAME")
    pool_size: int = Field(default=10, env="DB_POOL_SIZE")
    max_overflow: int = Field(default=20, env="DB_MAX_OVERFLOW")
    pool_timeout: int = Field(default=30, env="DB_POOL_TIMEOUT")
    echo: bool = Field(default=False, env="DB_ECHO")
    
    @property
    def url(self) -> str:
        """Generate database URL"""
        return f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class RedisSettings(BaseSettings):
    """Redis cache settings"""
    host: str = Field(default="localhost", env="REDIS_HOST")
    port: int = Field(default=6379, env="REDIS_PORT")
    password: Optional[str] = Field(default=None, env="REDIS_PASSWORD")
    db: int = Field(default=0, env="REDIS_DB")
    decode_responses: bool = Field(default=True, env="REDIS_DECODE_RESPONSES")
    socket_timeout: int = Field(default=5, env="REDIS_SOCKET_TIMEOUT")
    socket_connect_timeout: int = Field(default=5, env="REDIS_SOCKET_CONNECT_TIMEOUT")
    connection_pool_max_connections: int = Field(default=50, env="REDIS_POOL_MAX_CONNECTIONS")
    
    @property
    def url(self) -> str:
        """Generate Redis URL"""
        if self.password:
            return f"redis://:{self.password}@{self.host}:{self.port}/{self.db}"
        return f"redis://{self.host}:{self.port}/{self.db}"
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class MarketDataSettings(BaseSettings):
    """Market data API settings"""
    # Tushare API (primary data source)
    tushare_token: Optional[str] = Field(default=None, env="TUSHARE_TOKEN")
    
    # AkShare settings (backup data source, no token needed)
    akshare_enabled: bool = Field(default=True, env="AKSHARE_ENABLED")
    
    # JoinQuant API (alternative)
    joinquant_username: Optional[str] = Field(default=None, env="JOINQUANT_USERNAME")
    joinquant_password: Optional[str] = Field(default=None, env="JOINQUANT_PASSWORD")
    
    # Wind API (if available)
    wind_enabled: bool = Field(default=False, env="WIND_ENABLED")
    
    # Data update schedule
    update_schedule: str = Field(default="0 17 * * 1-5", env="DATA_UPDATE_SCHEDULE")  # 5PM weekdays
    intraday_update_interval: int = Field(default=60, env="INTRADAY_UPDATE_INTERVAL")  # seconds
    
    # Cache settings
    cache_ttl: int = Field(default=300, env="MARKET_DATA_CACHE_TTL")  # 5 minutes
    historical_cache_days: int = Field(default=365, env="HISTORICAL_CACHE_DAYS")
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class WebSocketSettings(BaseSettings):
    """WebSocket configuration for real-time data"""
    enabled: bool = Field(default=True, env="WEBSOCKET_ENABLED")
    heartbeat_interval: int = Field(default=30, env="WS_HEARTBEAT_INTERVAL")
    reconnect_interval: int = Field(default=5, env="WS_RECONNECT_INTERVAL")
    max_connections: int = Field(default=100, env="WS_MAX_CONNECTIONS")
    message_queue_size: int = Field(default=1000, env="WS_MESSAGE_QUEUE_SIZE")
    
    # Market data WebSocket endpoints
    sina_ws_url: str = Field(
        default="wss://hq.sinajs.cn/wskt",
        env="SINA_WS_URL"
    )
    eastmoney_ws_url: str = Field(
        default="wss://push2.eastmoney.com/websocket",
        env="EASTMONEY_WS_URL"
    )
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class ApplicationSettings(BaseSettings):
    """General application settings"""
    app_name: str = Field(default="Momentum Lens", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    debug: bool = Field(default=False, env="DEBUG")
    testing: bool = Field(default=False, env="TESTING")
    
    # API settings
    api_prefix: str = Field(default="/api", env="API_PREFIX")
    api_version: str = Field(default="v1", env="API_VERSION")
    
    # CORS settings
    cors_origins: list = Field(
        default=["http://localhost:3000", "http://127.0.0.1:3000"],
        env="CORS_ORIGINS"
    )
    cors_allow_credentials: bool = Field(default=True, env="CORS_ALLOW_CREDENTIALS")
    cors_allow_methods: list = Field(default=["*"], env="CORS_ALLOW_METHODS")
    cors_allow_headers: list = Field(default=["*"], env="CORS_ALLOW_HEADERS")
    
    # Security settings
    secret_key: str = Field(
        default="your-secret-key-change-in-production",
        env="SECRET_KEY"
    )
    algorithm: str = Field(default="HS256", env="ALGORITHM")
    access_token_expire_minutes: int = Field(default=60 * 24, env="ACCESS_TOKEN_EXPIRE_MINUTES")
    
    # Logging
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    log_file: str = Field(default="momentum_lens.log", env="LOG_FILE")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        env="LOG_FORMAT"
    )
    
    # Performance settings
    workers: int = Field(default=4, env="WORKERS")
    worker_connections: int = Field(default=1000, env="WORKER_CONNECTIONS")
    keepalive: int = Field(default=5, env="KEEPALIVE")
    
    @validator("cors_origins", pre=True)
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class BacktestSettings(BaseSettings):
    """Backtesting configuration"""
    enabled: bool = Field(default=True, env="BACKTEST_ENABLED")
    start_date: str = Field(default="2020-01-01", env="BACKTEST_START_DATE")
    end_date: Optional[str] = Field(default=None, env="BACKTEST_END_DATE")
    initial_capital: float = Field(default=1000000.0, env="BACKTEST_INITIAL_CAPITAL")
    commission_rate: float = Field(default=0.0003, env="BACKTEST_COMMISSION_RATE")
    slippage_rate: float = Field(default=0.001, env="BACKTEST_SLIPPAGE_RATE")
    benchmark: str = Field(default="000300", env="BACKTEST_BENCHMARK")  # CSI 300
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class NotificationSettings(BaseSettings):
    """Notification and alert settings"""
    enabled: bool = Field(default=True, env="NOTIFICATIONS_ENABLED")
    
    # Email settings
    email_enabled: bool = Field(default=False, env="EMAIL_ENABLED")
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: int = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    email_from: Optional[str] = Field(default=None, env="EMAIL_FROM")
    email_to: Optional[list] = Field(default=None, env="EMAIL_TO")
    
    # WeChat Work settings
    wechat_enabled: bool = Field(default=False, env="WECHAT_ENABLED")
    wechat_webhook: Optional[str] = Field(default=None, env="WECHAT_WEBHOOK")
    
    # DingTalk settings
    dingtalk_enabled: bool = Field(default=False, env="DINGTALK_ENABLED")
    dingtalk_webhook: Optional[str] = Field(default=None, env="DINGTALK_WEBHOOK")
    dingtalk_secret: Optional[str] = Field(default=None, env="DINGTALK_SECRET")
    
    @validator("email_to", pre=True)
    def parse_email_to(cls, v):
        if isinstance(v, str):
            return [email.strip() for email in v.split(",")]
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


class Settings:
    """Main settings aggregator"""
    
    def __init__(self):
        self.database = DatabaseSettings()
        self.redis = RedisSettings()
        self.market_data = MarketDataSettings()
        self.websocket = WebSocketSettings()
        self.application = ApplicationSettings()
        self.backtest = BacktestSettings()
        self.notifications = NotificationSettings()
    
    def validate_settings(self) -> bool:
        """Validate all settings"""
        errors = []
        
        # Check database connection
        if not self.database.password and not self.application.testing:
            errors.append("Database password is not set")
        
        # Check market data source
        if not self.market_data.tushare_token and not self.market_data.akshare_enabled:
            errors.append("No market data source configured")
        
        # Check secret key
        if self.application.secret_key == "your-secret-key-change-in-production" and not self.application.debug:
            errors.append("Secret key must be changed in production")
        
        if errors:
            raise ValueError(f"Configuration errors: {', '.join(errors)}")
        
        return True


# Singleton instance
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """Get singleton settings instance"""
    global _settings
    if _settings is None:
        _settings = Settings()
        if not os.getenv("TESTING"):
            _settings.validate_settings()
    return _settings