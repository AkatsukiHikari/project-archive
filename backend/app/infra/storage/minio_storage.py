import json
import logging
from minio import Minio
from minio.error import S3Error
from datetime import timedelta
from typing import BinaryIO
from app.core.config import settings
from app.infra.storage.adapter import StorageAdapter

logger = logging.getLogger(__name__)


class MinioAdapter(StorageAdapter):
    """
    MinIO 官方 Python SDK 适配器。

    存储策略：
        - avatars / thumbnails 等基础资源：bucket 设为公开，存永久直链 URL
        - archives / sensitive 等档案资源：bucket 保持私有，访问时生成 presigned URL
    """

    def __init__(self):
        endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        self.client = Minio(
            endpoint=endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE,
        )

    # ─── 存储桶管理 ──────────────────────────────────────────────────

    def _ensure_bucket(self, bucket: str, public: bool = False) -> None:
        """
        确保存储桶存在。若不存在则创建。
        public=True 时同时设置公开读取策略（适合头像、缩略图等）。
        """
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"已创建 MinIO 存储桶: {bucket}")
            if public:
                self._set_public_read_policy(bucket)
        except S3Error as e:
            logger.warning(f"存储桶初始化失败 {bucket}: {e}")

    def _set_public_read_policy(self, bucket: str) -> None:
        """为指定桶设置公开只读策略（任何人可 GET，不可写）"""
        policy = {
            "Version": "2012-10-17",
            "Statement": [
                {
                    "Effect": "Allow",
                    "Principal": {"AWS": ["*"]},
                    "Action": ["s3:GetObject"],
                    "Resource": [f"arn:aws:s3:::{bucket}/*"],
                }
            ],
        }
        try:
            self.client.set_bucket_policy(bucket, json.dumps(policy))
            logger.info(f"已设置 {bucket} 为公开读取")
        except S3Error as e:
            logger.warning(f"设置公开策略失败 {bucket}: {e}")

    def get_public_url(self, filename: str, bucket: str) -> str:
        """
        构造永久公开访问 URL（适用于公开 bucket）。
        格式：{MINIO_PUBLIC_URL}/{bucket}/{filename}
        不会过期，直接存入数据库。
        """
        base = settings.MINIO_PUBLIC_URL.rstrip("/")
        return f"{base}/{bucket}/{filename}"

    # ─── 核心 StorageAdapter 接口 ───────────────────────────────────

    def save(self, file_object: BinaryIO, filename: str, bucket: str, content_type: str = "application/octet-stream") -> str:
        """上传文件到 MinIO。返回 object name（文件名）。"""
        try:
            # 判断是否为公开 bucket（头像等基础资源）
            public_buckets = {"avatars", "thumbnails", "public"}
            is_public = bucket in public_buckets
            self._ensure_bucket(bucket, public=is_public)

            file_object.seek(0, 2)
            size = file_object.tell()
            file_object.seek(0)

            self.client.put_object(
                bucket_name=bucket,
                object_name=filename,
                data=file_object,
                length=size,
                content_type=content_type,
            )
            return filename
        except S3Error as e:
            logger.error(f"MinIO 上传失败: {e}")
            raise

    def get_presigned_url(self, filename: str, bucket: str, expires_seconds: int = 3600) -> str:
        """
        生成预签名临时访问 URL（用于私有 bucket 的档案资源）。
        对于 avatars 等公开 bucket，请直接使用 get_public_url() 或存储的永久 URL。
        """
        try:
            return self.client.get_presigned_url(
                "GET",
                bucket,
                filename,
                expires=timedelta(seconds=expires_seconds),
            )
        except S3Error as e:
            logger.error(f"MinIO 预签名链接生成失败: {e}")
            raise

    def delete(self, filename: str, bucket: str) -> bool:
        try:
            self.client.remove_object(bucket, filename)
            return True
        except S3Error as e:
            logger.error(f"MinIO 删除失败: {e}")
            return False

    def exists(self, filename: str, bucket: str) -> bool:
        try:
            self.client.stat_object(bucket, filename)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"MinIO 存在性检查失败: {e}")
            return False