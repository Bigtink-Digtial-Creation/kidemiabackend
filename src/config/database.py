from typing import Generator
from contextlib import contextmanager

from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import NullPool, QueuePool

from src.config.settings import settings


def get_database_engine():
    """
    Create and configure database engine.
    Supports switching between different databases.
    """
    engine_kwargs = {
        "echo": settings.DB_ECHO,
        "future": True,  # Use SQLAlchemy 2.0 style
    }

    # Configure connection pool
    if settings.ENVIRONMENT == "testing":
        engine_kwargs["poolclass"] = NullPool
    else:
        engine_kwargs["poolclass"] = QueuePool
        engine_kwargs["pool_size"] = settings.DB_POOL_SIZE
        engine_kwargs["max_overflow"] = settings.DB_MAX_OVERFLOW
        engine_kwargs["pool_pre_ping"] = True  # Verify connections before using

    # Create engine
    database_url = str(settings.DATABASE_URL)
    engine = create_engine(database_url, **engine_kwargs)

    # Add event listeners
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        """Enable foreign keys for SQLite (if using SQLite for testing)"""
        if "sqlite" in database_url:
            cursor = dbapi_conn.cursor()
            cursor.execute("PRAGMA foreign_keys=ON")
            cursor.close()

    return engine


# Create engine instance
engine = get_database_engine()

# Create session factory
SessionLocal = sessionmaker(
    autocommit=False, autoflush=False, bind=engine, expire_on_commit=False
)


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency for database sessions.
    Automatically handles session lifecycle.

    Usage:
        @app.get("/users")
        def get_users(db: Session = Depends(get_db)):
            return db.query(User).all()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@contextmanager
def get_db_context():
    """
    Context manager for database sessions.
    Use in background tasks or outside of FastAPI request context.

    Usage:
        with get_db_context() as db:
            user = db.query(User).first()
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


class DatabaseSession:
    """
    Database session wrapper with transaction support.
    Useful for complex operations that need explicit transaction control.
    """

    def __init__(self, db: Session):
        self.db = db
        self._transaction_depth = 0

    def begin(self):
        """Begin a transaction"""
        if self._transaction_depth == 0:
            self.db.begin()
        self._transaction_depth += 1

    def commit(self):
        """Commit the transaction"""
        if self._transaction_depth == 1:
            self.db.commit()
        self._transaction_depth = max(0, self._transaction_depth - 1)

    def rollback(self):
        """Rollback the transaction"""
        if self._transaction_depth > 0:
            self.db.rollback()
            self._transaction_depth = 0

    def __enter__(self):
        self.begin()
        return self.db

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_type is not None:
            self.rollback()
        else:
            self.commit()


def create_tables():
    """Create all tables in the database"""
    from src.shared.database.base import Base

    Base.metadata.create_all(bind=engine)


def drop_tables():
    """Drop all tables in the database"""
    from src.shared.database.base import Base

    Base.metadata.drop_all(bind=engine)


def reset_database():
    """Reset the database (drop and recreate all tables)"""
    drop_tables()
    create_tables()


async def check_db_connection() -> bool:
    """
    Check if database connection is healthy.
    Useful for health checks.
    """
    try:
        with get_db_context() as db:
            db.execute("SELECT *")
        return True
    except Exception:
        return False
