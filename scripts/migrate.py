#!/usr/bin/env python3
"""
Database migration script for Momentum Lens ETF trading system.
This script handles database schema migrations using Alembic.
"""

import os
import sys
import argparse
import logging
from typing import Optional
from pathlib import Path

# Add the backend directory to Python path
sys.path.insert(0, str(Path(__file__).parent.parent / "backend"))

try:
    import asyncio
    import psycopg2
    from psycopg2 import sql
    from alembic.config import Config
    from alembic import command
    from sqlalchemy import create_engine, text
    from sqlalchemy.exc import OperationalError
    
    from backend.config.settings import get_settings
    from backend.models.base import DatabaseManager
except ImportError as e:
    print(f"Error importing dependencies: {e}")
    print("Please ensure all required packages are installed:")
    print("pip install alembic psycopg2-binary sqlalchemy")
    sys.exit(1)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class MigrationManager:
    """Handles database migrations for the Momentum Lens system."""
    
    def __init__(self, database_url: Optional[str] = None):
        """Initialize the migration manager."""
        self.settings = get_settings()
        self.database_url = database_url or str(self.settings.database.url)
        self.alembic_cfg_path = Path(__file__).parent.parent / "backend" / "alembic.ini"
        
        # Parse database URL for admin operations
        self.db_params = self._parse_database_url()
        
    def _parse_database_url(self) -> dict:
        """Parse database URL into components."""
        from urllib.parse import urlparse
        
        parsed = urlparse(self.database_url)
        return {
            'host': parsed.hostname,
            'port': parsed.port or 5432,
            'database': parsed.path.lstrip('/'),
            'user': parsed.username,
            'password': parsed.password
        }
    
    def create_database(self) -> bool:
        """Create the database if it doesn't exist."""
        logger.info(f"Creating database '{self.db_params['database']}' if it doesn't exist...")
        
        try:
            # Connect to postgres database to create the target database
            admin_conn_str = (
                f"host={self.db_params['host']} "
                f"port={self.db_params['port']} "
                f"user={self.db_params['user']} "
                f"password={self.db_params['password']} "
                f"dbname=postgres"
            )
            
            conn = psycopg2.connect(admin_conn_str)
            conn.autocommit = True
            cursor = conn.cursor()
            
            # Check if database exists
            cursor.execute(
                "SELECT 1 FROM pg_database WHERE datname = %s",
                (self.db_params['database'],)
            )
            
            if cursor.fetchone() is None:
                # Create database
                cursor.execute(
                    sql.SQL("CREATE DATABASE {}").format(
                        sql.Identifier(self.db_params['database'])
                    )
                )
                logger.info(f"Database '{self.db_params['database']}' created successfully")
            else:
                logger.info(f"Database '{self.db_params['database']}' already exists")
            
            cursor.close()
            conn.close()
            return True
            
        except psycopg2.Error as e:
            logger.error(f"Error creating database: {e}")
            return False
    
    def check_connection(self) -> bool:
        """Check if database connection is working."""
        logger.info("Checking database connection...")
        
        try:
            engine = create_engine(self.database_url)
            with engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                result.fetchone()
            logger.info("Database connection successful")
            return True
            
        except OperationalError as e:
            logger.error(f"Database connection failed: {e}")
            return False
    
    def init_alembic(self) -> bool:
        """Initialize Alembic configuration."""
        logger.info("Initializing Alembic configuration...")
        
        try:
            # Create alembic directory structure
            alembic_dir = Path(__file__).parent.parent / "backend" / "alembic"
            alembic_dir.mkdir(exist_ok=True)
            
            # Create versions directory
            versions_dir = alembic_dir / "versions"
            versions_dir.mkdir(exist_ok=True)
            
            # Create alembic.ini if it doesn't exist
            if not self.alembic_cfg_path.exists():
                alembic_ini_content = f"""# Alembic configuration for Momentum Lens

[alembic]
# Path to migration scripts
script_location = backend/alembic

# Template used to generate migration file names; The default value is %%(rev)s_%%(slug)s
file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# sys.path path, will be prepended to sys.path if present.
prepend_sys_path = .

# Timezone to use when rendering the date within the migration file
# as well as the filename. If specified, requires the python-dateutil library
# that can be installed by adding `alembic[tz]` to the pip requirements
# string value is passed to dateutil.tz.gettz()
# leave blank for localtime
timezone = Asia/Shanghai

# Max length of characters to apply to the "slug" field
truncate_slug_length = 40

# Set to 'true' to run the environment during the 'revision' command,
# regardless of autogenerate
revision_environment = false

# Set to 'true' to allow .pyc and .pyo files without a source .py file
# to be detected as revisions in the versions/ directory
sourceless = false

# Version path separator; As mentioned above, this is the character used to split
# version_locations. The default within new alembic.ini files is "os", which uses
# os.pathsep. If this key is omitted entirely, it falls back to the legacy
# behavior of splitting on spaces and/or commas.
version_path_separator = :

# Version locations relative to the script location
version_locations = %(here)s/backend/alembic/versions

# Version naming pattern
version_name_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d_%%(rev)s_%%(slug)s

# The output encoding used when revision files are written from script.py.mako
output_encoding = utf-8

sqlalchemy.url = {self.database_url}

[post_write_hooks]
# Hooks to run after migration files are generated
# format using "black" - use the console_scripts runner, against the "black" entrypoint
hooks = black
black.type = console_scripts
black.entrypoint = black
black.options = -l 100

# Logging configuration
[loggers]
keys = root,sqlalchemy,alembic

[handlers]
keys = console

[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_sqlalchemy]
level = WARN
handlers =
qualname = sqlalchemy.engine

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
datefmt = %H:%M:%S
"""
                
                with open(self.alembic_cfg_path, 'w') as f:
                    f.write(alembic_ini_content)
                
                logger.info("Created alembic.ini configuration file")
            
            # Create env.py if it doesn't exist
            env_py_path = alembic_dir / "env.py"
            if not env_py_path.exists():
                env_py_content = '''"""Alembic environment configuration for Momentum Lens."""

import asyncio
import logging
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool
from alembic import context

# Import your models here for autogenerate support
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))

from backend.models.base import Base
from backend.models import etf, market, portfolio, user

# This is the Alembic Config object
config = context.config

# Interpret the config file for Python logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger('alembic.env')

# Add your model's MetaData object here
target_metadata = Base.metadata

# Other values from the config
exclude_tables = ['spatial_ref_sys']


def get_url():
    """Get database URL from config."""
    return config.get_main_option("sqlalchemy.url")


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        include_object=include_object,
    )

    with context.begin_transaction():
        context.run_migrations()


def include_object(object, name, type_, reflected, compare_to):
    """Include object function for filtering."""
    if type_ == "table" and name in exclude_tables:
        return False
    return True


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            include_object=include_object,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
'''
                
                with open(env_py_path, 'w') as f:
                    f.write(env_py_content)
                
                logger.info("Created env.py environment file")
            
            # Create script.py.mako template
            template_path = alembic_dir / "script.py.mako"
            if not template_path.exists():
                template_content = '''"""${message}

Revision ID: ${up_revision}
Revises: ${down_revision | comma,n}
Create Date: ${create_date}

"""
from alembic import op
import sqlalchemy as sa
${imports if imports else ""}

# revision identifiers, used by Alembic.
revision = ${repr(up_revision)}
down_revision = ${repr(down_revision)}
branch_labels = ${repr(branch_labels)}
depends_on = ${repr(depends_on)}


def upgrade() -> None:
    ${upgrades if upgrades else "pass"}


def downgrade() -> None:
    ${downgrades if downgrades else "pass"}
'''
                
                with open(template_path, 'w') as f:
                    f.write(template_content)
                
                logger.info("Created script.py.mako template")
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing Alembic: {e}")
            return False
    
    def create_initial_migration(self) -> bool:
        """Create initial migration."""
        logger.info("Creating initial migration...")
        
        try:
            alembic_cfg = Config(str(self.alembic_cfg_path))
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
            command.revision(
                alembic_cfg,
                message="Initial migration",
                autogenerate=True
            )
            
            logger.info("Initial migration created successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error creating initial migration: {e}")
            return False
    
    def run_migrations(self) -> bool:
        """Run database migrations."""
        logger.info("Running database migrations...")
        
        try:
            alembic_cfg = Config(str(self.alembic_cfg_path))
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
            command.upgrade(alembic_cfg, "head")
            
            logger.info("Database migrations completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error running migrations: {e}")
            return False
    
    def rollback_migration(self, revision: str = "-1") -> bool:
        """Rollback to a specific migration."""
        logger.info(f"Rolling back to revision: {revision}")
        
        try:
            alembic_cfg = Config(str(self.alembic_cfg_path))
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
            command.downgrade(alembic_cfg, revision)
            
            logger.info(f"Rollback to {revision} completed successfully")
            return True
            
        except Exception as e:
            logger.error(f"Error rolling back migration: {e}")
            return False
    
    def get_current_revision(self) -> Optional[str]:
        """Get current database revision."""
        try:
            alembic_cfg = Config(str(self.alembic_cfg_path))
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
            from alembic.runtime.migration import MigrationContext
            from sqlalchemy import create_engine
            
            engine = create_engine(self.database_url)
            with engine.connect() as connection:
                context = MigrationContext.configure(connection)
                return context.get_current_revision()
                
        except Exception as e:
            logger.error(f"Error getting current revision: {e}")
            return None
    
    def show_migration_history(self) -> bool:
        """Show migration history."""
        logger.info("Migration history:")
        
        try:
            alembic_cfg = Config(str(self.alembic_cfg_path))
            alembic_cfg.set_main_option("sqlalchemy.url", self.database_url)
            
            command.history(alembic_cfg, verbose=True)
            return True
            
        except Exception as e:
            logger.error(f"Error showing migration history: {e}")
            return False


def main():
    """Main function for command line usage."""
    parser = argparse.ArgumentParser(
        description="Database migration script for Momentum Lens"
    )
    parser.add_argument(
        "command",
        choices=[
            "init", "create-db", "check", "migrate", "rollback", 
            "status", "history", "create-migration"
        ],
        help="Migration command to execute"
    )
    parser.add_argument(
        "--database-url",
        help="Database URL (overrides default from settings)"
    )
    parser.add_argument(
        "--revision",
        default="-1",
        help="Revision for rollback (default: -1 for previous)"
    )
    parser.add_argument(
        "--message",
        help="Message for new migration"
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize migration manager
    migration_manager = MigrationManager(args.database_url)
    
    success = True
    
    if args.command == "create-db":
        success = migration_manager.create_database()
        
    elif args.command == "check":
        success = migration_manager.check_connection()
        
    elif args.command == "init":
        success = (
            migration_manager.create_database() and
            migration_manager.check_connection() and
            migration_manager.init_alembic()
        )
        
    elif args.command == "migrate":
        success = migration_manager.run_migrations()
        
    elif args.command == "rollback":
        success = migration_manager.rollback_migration(args.revision)
        
    elif args.command == "status":
        current_revision = migration_manager.get_current_revision()
        if current_revision:
            logger.info(f"Current revision: {current_revision}")
        else:
            logger.info("No migrations have been applied")
        success = current_revision is not None
        
    elif args.command == "history":
        success = migration_manager.show_migration_history()
        
    elif args.command == "create-migration":
        if not args.message:
            logger.error("Message is required for creating migrations")
            success = False
        else:
            success = migration_manager.create_initial_migration()
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()