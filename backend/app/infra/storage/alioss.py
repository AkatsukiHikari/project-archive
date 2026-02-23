import logging
import oss2
from typing import BinaryIO
from app.core.config import settings
from app.infra.storage.adapter import StorageAdapter

logger = logging.getLogger(__name__)

class AliOSSAdapter(StorageAdapter):
    """
    阿里云 OSS 官方适配器 (oss2)。

    使用场景：
        中国区域部署。
        使用阿里云对象存储服务（OSS）。

    Attributes:
        auth (oss2.Auth): 认证对象，包含 AccessKeyId 和 AccessKeySecret。
        endpoint (str): OSS 服务端点（如 oss-cn-hangzhou.aliyuncs.com）。
    """
    
    def __init__(self):
        """
        初始化阿里云 OSS 适配器。
        
        从配置读取 OSS_ACCESS_KEY_ID 和 OSS_ACCESS_KEY_SECRET。
        注意：OSS 的 Bucket 对象是操作的入口，每次操作前需通过 _get_bucket 获取。
        """
        # 快速检查：如果 Access Key 未配置，发出警告
        if not getattr(settings, "OSS_ACCESS_KEY_ID", None):
            logger.warning("AliOSS 凭据未配置，适配器可能无法工作。")
            
        self.auth = oss2.Auth(
            settings.OSS_ACCESS_KEY_ID, 
            settings.OSS_ACCESS_KEY_SECRET
        )
        self.endpoint = settings.OSS_ENDPOINT

    def _get_bucket(self, bucket_name: str) -> oss2.Bucket:
        """
        内部辅助方法：获取指定的 OSS Bucket 实例。

        Args:
            bucket_name (str): 存储桶名称。

        Returns:
            oss2.Bucket: 可用于操作该桶的对象。
        """
        return oss2.Bucket(self.auth, self.endpoint, bucket_name)

    def save(self, file_object: BinaryIO, filename: str, bucket: str, content_type: str = "application/octet-stream") -> str:
        """
        上传文件到阿里云 OSS。

        逻辑：
        OSS put_object 支持文件流（需支持 read 方法）。
        自动设置 Content-Type。

        Returns:
            str: 上传成功的文件名（Key）。

        Raises:
            oss2.exceptions.OssError: 如果上传过程中 OSS 返回错误。
        """
        try:
            b = self._get_bucket(bucket)
            
            # 重置文件指针
            file_object.seek(0)
            
            # OSS 上传：支持流式上传
            b.put_object(filename, file_object, headers={'Content-Type': content_type})
            return filename
        except oss2.exceptions.OssError as e:
            logger.error(f"AliOSS 上传失败: {e}")
            raise

    def get_presigned_url(self, filename: str, bucket: str, expires_seconds: int = 3600) -> str:
        """
        生成 OSS 预签名下载链接。

        Returns:
            str: 临时下载链接。
        """
        try:
            b = self._get_bucket(bucket)
            return b.sign_url('GET', filename, expires_seconds)
        except oss2.exceptions.OssError as e:
            logger.error(f"AliOSS 预签名链接生成失败: {e}")
            raise

    def delete(self, filename: str, bucket: str) -> bool:
        """
        删除 OSS 对象。

        Returns:
            bool: 成功 True，失败 False。
        """
        try:
            b = self._get_bucket(bucket)
            b.delete_object(filename)
            return True
        except oss2.exceptions.OssError as e:
            logger.error(f"AliOSS 删除失败: {e}")
            return False

    def exists(self, filename: str, bucket: str) -> bool:
        """
        检查 OSS 对象是否存在。

        Returns:
            bool: 存在 True，不存在 False。
        """
        try:
            b = self._get_bucket(bucket)
            return b.object_exists(filename)
        except oss2.exceptions.OssError:
            return False