from sqlalchemy.orm import Session
from src.domains.settings.models.platform_settings import PlatformSetting
from src.config.settings import settings
from src.core.security import decrypt_value
from src.config.database import SessionLocal  # Import your session factory here


class ConfigService:
    @staticmethod
    def get_value(key: str, default: any = None, db: Session = None):
        """
        Helper to get a DB value or fallback to .env.
        If 'db' is not passed, it creates a temporary session.
        """
        if not settings.ALLOW_DB_CONFIG_OVERRIDE:
            return default

        # Use provided db session, or create a fresh one if needed
        if db:
            return ConfigService._fetch_from_db(db, key, default)
        else:
            # Context manager ensures the session is closed after the query
            with SessionLocal() as standalone_db:
                return ConfigService._fetch_from_db(standalone_db, key, default)

    @staticmethod
    def _fetch_from_db(db: Session, key: str, default: any):
        """Internal logic to query the database"""
        db_val = (
            db.query(PlatformSetting)
            .filter(
                PlatformSetting.key == key.lower(),
                PlatformSetting.is_active.is_(True),
            )
            .first()
        )

        if not db_val:
            return default

        value = db_val.value

        if db_val.is_secret:
            try:
                return decrypt_value(value)
            except Exception as e:
                raise RuntimeError(
                    f"Failed to decrypt secret config '{db_val.key}'"
                ) from e

        return value
