"""
Database base configuration and session management.
"""

from sqlalchemy import create_engine, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, scoped_session
from sqlalchemy.pool import NullPool, QueuePool
from contextlib import contextmanager
from typing import Generator
import logging

from backend.config.settings import get_settings

logger = logging.getLogger(__name__)

# Get database settings
settings = get_settings()

# Fallback to SQLite if psycopg2 is unavailable
try:  # pragma: no cover - runtime dependency check
    import psycopg2  # type: ignore
    database_url = settings.database.url
    engine = create_engine(
        database_url,
        poolclass=QueuePool,
        pool_size=settings.database.pool_size,
        max_overflow=settings.database.max_overflow,
        pool_timeout=settings.database.pool_timeout,
        pool_recycle=3600,  # Recycle connections after 1 hour
        echo=settings.database.echo,
        future=True,
    )
except ModuleNotFoundError:
    logger.warning("psycopg2 not installed, using in-memory SQLite database")
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=NullPool,
        future=True,
    )

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False
)

# Create scoped session for thread safety
db_session = scoped_session(SessionLocal)

# Create base class for models
metadata = MetaData(
    naming_convention={
        "ix": "ix_%(column_0_label)s",
        "uq": "uq_%(table_name)s_%(column_0_name)s",
        "ck": "ck_%(table_name)s_%(constraint_name)s",
        "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
        "pk": "pk_%(table_name)s"
    }
)

Base = declarative_base(metadata=metadata)

# Add query property to Base
Base.query = db_session.query_property()


def init_db():
    """Initialize database, create all tables"""
    try:
        # Import all models to ensure they are registered
        from . import etf, portfolio, market, user
        
        # Create all tables
        Base.metadata.create_all(bind=engine)
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise


def drop_db():
    """Drop all tables (use with caution)"""
    try:
        Base.metadata.drop_all(bind=engine)
        logger.info("All tables dropped successfully")
    except Exception as e:
        logger.error(f"Failed to drop tables: {e}")
        raise


@contextmanager
def get_db() -> Generator:
    """
    Get database session.
    Usage:
        with get_db() as db:
            db.query(Model).all()
    """
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception as e:
        session.rollback()
        logger.error(f"Database session error: {e}")
        raise
    finally:
        session.close()


def get_db_dependency():
    """
    Dependency for FastAPI endpoints.
    Usage:
        @app.get("/items")
        def get_items(db: Session = Depends(get_db_dependency)):
            return db.query(Item).all()
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


class DatabaseManager:
    """Database management utilities"""
    
    @staticmethod
    def check_connection() -> bool:
        """Check if database connection is alive"""
        try:
            with engine.connect() as conn:
                conn.execute("SELECT 1")
            return True
        except Exception as e:
            logger.error(f"Database connection check failed: {e}")
            return False
    
    @staticmethod
    def get_table_stats() -> dict:
        """Get statistics for all tables"""
        stats = {}
        try:
            with get_db() as db:
                for table in Base.metadata.tables.keys():
                    count = db.execute(f"SELECT COUNT(*) FROM {table}").scalar()
                    stats[table] = count
        except Exception as e:
            logger.error(f"Failed to get table statistics: {e}")
        return stats
    
    @staticmethod
    def vacuum_analyze():
        """Run VACUUM ANALYZE on PostgreSQL database"""
        if engine.dialect.name != "postgresql":
            logger.warning("VACUUM ANALYZE skipped: not using PostgreSQL")
            return
        try:
            with engine.connect() as conn:
                conn.execute("VACUUM ANALYZE")
                logger.info("VACUUM ANALYZE completed successfully")
        except Exception as e:
            logger.error(f"Failed to run VACUUM ANALYZE: {e}")
    
    @staticmethod
    def backup_database(backup_path: str):
        """Create database backup (PostgreSQL specific)"""
        if engine.dialect.name != "postgresql":
            logger.warning("Backup skipped: not using PostgreSQL")
            return
        import subprocess
        try:
            cmd = [
                "pg_dump",
                "-h", settings.database.host,
                "-p", str(settings.database.port),
                "-U", settings.database.user,
                "-d", settings.database.database,
                "-f", backup_path
            ]
            subprocess.run(cmd, check=True, env={"PGPASSWORD": settings.database.password})
            logger.info(f"Database backed up to {backup_path}")
        except Exception as e:
            logger.error(f"Failed to backup database: {e}")
            raise
