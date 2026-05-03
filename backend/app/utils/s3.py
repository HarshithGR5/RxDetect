"""
s3.py
AWS S3 helper functions for uploading and generating pre-signed URLs.
"""
import structlog
import boto3
from botocore.exceptions import ClientError
from app.config import settings

log = structlog.get_logger(__name__)


def _s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=settings.aws_access_key_id,
        aws_secret_access_key=settings.aws_secret_access_key,
        region_name=settings.aws_region,
    )


def upload_file(local_path: str, s3_key: str, content_type: str = "application/octet-stream") -> bool:
    """Upload a local file to S3. Returns True on success."""
    try:
        _s3_client().upload_file(
            local_path,
            settings.aws_s3_bucket,
            s3_key,
            ExtraArgs={"ContentType": content_type},
        )
        log.info("s3.upload_success", key=s3_key)
        return True
    except ClientError as e:
        log.error("s3.upload_error", key=s3_key, error=str(e))
        return False


def upload_bytes(data: bytes, s3_key: str, content_type: str = "application/octet-stream") -> bool:
    """Upload raw bytes to S3."""
    try:
        _s3_client().put_object(
            Bucket=settings.aws_s3_bucket,
            Key=s3_key,
            Body=data,
            ContentType=content_type,
        )
        log.info("s3.upload_bytes_success", key=s3_key)
        return True
    except ClientError as e:
        log.error("s3.upload_bytes_error", key=s3_key, error=str(e))
        return False


def generate_presigned_url(s3_key: str, expiry_seconds: int = 3600) -> str | None:
    """Return a pre-signed download URL valid for `expiry_seconds`."""
    try:
        url = _s3_client().generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.aws_s3_bucket, "Key": s3_key},
            ExpiresIn=expiry_seconds,
        )
        return url
    except ClientError as e:
        log.error("s3.presigned_error", key=s3_key, error=str(e))
        return None


def delete_object(s3_key: str) -> bool:
    try:
        _s3_client().delete_object(Bucket=settings.aws_s3_bucket, Key=s3_key)
        log.info("s3.deleted", key=s3_key)
        return True
    except ClientError as e:
        log.error("s3.delete_error", key=s3_key, error=str(e))
        return False