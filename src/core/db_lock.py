from sqlalchemy.orm import Session
from sqlalchemy import text


def acquire_db_lock(db: Session, lock_key: str):
    """
    Transaction-scoped advisory lock.
    Automatically released when transaction ends.
    """
    db.execute(
        text("SELECT pg_advisory_xact_lock(hashtext(:key))"),
        {"key": lock_key},
    )
