import os
from dotenv import load_dotenv

load_dotenv()


class GCSConfig:
    """Google Cloud Storage configuration"""

    BUCKET_NAME = os.getenv("GCS_BUCKET_NAME", "kidemia_bucket")
    # CREDENTIALS_PATH = os.getenv("GOOGLE_APPLICATION_CREDENTIALS",)
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}
    ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
    }
