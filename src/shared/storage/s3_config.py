import os


class S3Config:
    ACCESS_KEY = os.getenv("S3_ACCESS_KEY")
    SECRET_KEY = os.getenv("S3_SECRET_KEY")
    BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
    ENDPOINT_URL = os.getenv("S3_ENDPOINT_URL")
    TENANT_ID = os.getenv("S3_TENANT_ID")

    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".pdf"}
    ALLOWED_MIME_TYPES = {
        "image/jpeg",
        "image/png",
        "image/gif",
        "image/webp",
        "application/pdf",
    }
