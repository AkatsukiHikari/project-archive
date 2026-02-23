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

    使用场景：
        私有化部署（Docker / K8s）的 MinIO 集群。
        完全兼容 Amazon S3 API，但使用 MinIO 自己的高性能库进行优化。

    Attributes:
        client (Minio): 已初始化的 MinIO 客户端实例。
    """
    
    def __init__(self):
        """
        初始化 MinIO 客户端。
        从配置中读取端点、密钥和安全设置。
        """
        # 快速检查：如果端点未配置，发出警告
        if not settings.MINIO_ENDPOINT:
            logger.warning("MinIO endpoint 未配置，存储适配器可能无法工作。")

        # 移除协议前缀（MinIO 库需要纯 host:port 格式）
        endpoint = settings.MINIO_ENDPOINT.replace("http://", "").replace("https://", "")
        
        self.client = Minio(
            endpoint=endpoint,
            access_key=settings.MINIO_ACCESS_KEY,
            secret_key=settings.MINIO_SECRET_KEY,
            secure=settings.MINIO_SECURE  # False (开发环境) 或 True (生产环境，需配置 HTTPS)
        )

    def _ensure_bucket(self, bucket: str):
        """
        内部辅助方法：确保存储桶存在。
        
        如果桶不存在，尝试创建它。如果已存在，记录日志并返回。
        此方法可以防止应用启动时因缺少桶而崩溃。

        Args:
            bucket (str): 存储桶名称。
        """
        try:
            if not self.client.bucket_exists(bucket):
                self.client.make_bucket(bucket)
                logger.info(f"已创建 MinIO 存储桶: {bucket}")
        except S3Error as e:
            logger.warning(f"无法检查或创建 MinIO 存储桶 {bucket}: {e}")

    def save(self, file_object: BinaryIO, filename: str, bucket: str, content_type: str = "application/octet-stream") -> str:
        """
        上传文件到 MinIO。

        逻辑：
        1. 检查桶是否存在。
        2. 计算文件大小（MinIO put_object 需要 content-length）。
        3. 上传数据。

        Returns:
            str: 上传成功的文件名（Object Key）。

        Raises:
            S3Error: 如果上传过程中 MinIO 返回错误。
        """
        try:
            self._ensure_bucket(bucket)
            
            # 计算大小：MinIO 需要确切的 length
            file_object.seek(0, 2)
            size = file_object.tell()
            file_object.seek(0)
            
            self.client.put_object(
                bucket_name=bucket,
                object_name=filename,
                data=file_object,
                length=size,
                content_type=content_type
            )
            return filename
        except S3Error as e:
            logger.error(f"MinIO 上传失败: {e}")
            raise

    def get_presigned_url(self, filename: str, bucket: str, expires_seconds: int = 3600) -> str:
        """
        生成 MinIO 预签名 URL。

        Returns:
            str: 临时下载链接。
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
        """
        删除 MinIO 对象。

        Returns:
            bool: 成功 True，失败 False。
        """
        try:
            self.client.remove_object(bucket, filename)
            return True
        except S3Error as e:
            logger.error(f"MinIO 删除失败: {e}")
            return False

    def exists(self, filename: str, bucket: str) -> bool:
        """
        检查 MinIO 对象是否存在（使用 stat_object）。

        Returns:
            bool: 存在 True，不存在 False。
        """
        try:
            self.client.stat_object(bucket, filename)
            return True
        except S3Error as e:
            if e.code == "NoSuchKey":
                return False
            logger.error(f"MinIO 存在性检查失败: {e}")
            return False