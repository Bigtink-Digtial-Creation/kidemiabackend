from contextlib import contextmanager, asynccontextmanager
from src.config.database import get_db, get_async_db


@contextmanager
def get_sync_db_session():
    """Wrap sync db generator in context manager"""
    db = next(get_db())
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@asynccontextmanager
async def get_async_db_session():
    """Wrap async db generator in async context manager"""
    db_gen = get_async_db()
    db = await anext(db_gen)
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
    finally:
        await db.close()
