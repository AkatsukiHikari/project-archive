import logging
import boto3
from botocore.exceptions import ClientError
from typing import BinaryIO
from app.core.config import settings
from app.infra.storage.adapter import StorageAdapter

logger = logging.getLogger(__name__)

class AWSS3Adapter(StorageAdapter):
    """
    AWS S3 官方适配器 (Boto3)。
    
    使用场景：
        生产环境部署在 AWS。
        使用 IAM 角色或 Access Key 访问 S3 桶。
        严格遵循 AWS 标准最佳实践。

    Attributes:
        s3_client (botocore.client.S3): Boto3 初始化的 S3 客户端。
    """
    
    def __init__(self):
        """
        初始化 AWS S3 客户端。
        从配置中读取密钥和区域信息。
        如果凭据缺失，记录警告日志（但在真正调用方法前不会抛出错误）。
        """
        # 快速检查：如果 Access Key 未配置，发出警告
        if not getattr(settings, "AWS_ACCESS_KEY_ID", None):
             logger.warning("AWS 凭据未配置，S3 适配器可能无法工作。")

        self.s3_client = boto3.client(
            's3',
            aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
            aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
            region_name=settings.AWS_REGION
        )

    def save(self, file_object: BinaryIO, filename: str, bucket: str, content_type: str = "application/octet-stream") -> str:
        """
        上传文件到 AWS S3。

        逻辑：
        使用 Boto3 的 `upload_fileobj`，它会自动处理分片上传（Multipart Upload），适合大文件。
        需要确保文件指针在开头。

        Returns:
            str: 上传成功的文件名（Key）。

        Raises:
            ClientError: 如果 AWS API 返回错误（如 403 Forbidden）。
        """
        try:
            # 确保指针归零
            file_object.seek(0)
            
            self.s3_client.upload_fileobj(
                file_object, 
                bucket, 
                filename, 
                ExtraArgs={'ContentType': content_type}
            )
            return filename
        except ClientError as e:
            logger.error(f"AWS S3 上传失败: {e}")
            raise

    def get_public_url(self, filename: str, bucket: str) -> str:
        """AWS S3: 构造标准路径格式公开 URL（需 bucket 设为 public read）。"""
        region = settings.AWS_REGION
        return f"https://{bucket}.s3.{region}.amazonaws.com/{filename}"

    def get_presigned_url(self, filename: str, bucket: str, expires_seconds: int = 3600) -> str:
        """
        生成 AWS S3 预签名 URL。

        Returns:
            str: 临时下载链接。
        """
        try:
            url = self.s3_client.generate_presigned_url(
                ClientMethod='get_object',
                Params={'Bucket': bucket, 'Key': filename},
                ExpiresIn=expires_seconds
            )
            return url
        except ClientError as e:
            logger.error(f"AWS S3 预签名链接生成失败: {e}")
            raise

    def delete(self, filename: str, bucket: str) -> bool:
        """
        删除 AWS S3 对象。

        Returns:
            bool: 成功 True，失败 False。
        """
        try:
            self.s3_client.delete_object(Bucket=bucket, Key=filename)
            return True
        except ClientError as e:
            logger.error(f"AWS S3 删除失败: {e}")
            return False

    def exists(self, filename: str, bucket: str) -> bool:
        """
        检查 AWS S3 对象是否存在（使用 head_object）。

        Returns:
            bool: 存在 True，不存在（404）False。
        """
        try:
            self.s3_client.head_object(Bucket=bucket, Key=filename)
            return True
        except ClientError as e:
            if e.response['Error']['Code'] == "404":
                return False
            # 其他错误（如 403 Forbidden）记录日志并返回 False（或者是 True 但不可访问）
            logger.error(f"AWS S3 存在性检查失败: {e}")
            return False