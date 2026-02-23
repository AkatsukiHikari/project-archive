from app.core.config import settings
from .adapter import StorageAdapter
from .local import LocalAdapter
from .minio_storage import MinioAdapter
from .aws_s3 import AWSS3Adapter
from .alioss import AliOSSAdapter

class StorageFactory:
    """
    存储适配器工厂类。
    
    使用场景：
        应用程序启动时，根据配置的 STORAGE_TYPE 自动加载正确的存储实现。
        业务代码无需关心底层是本地磁盘还是云存储，只需通过此工厂获取适配器实例。

    支持的存储类型：
        - "local": 本地文件系统 (默认)
        - "aws" / "s3": AWS S3 兼容对象存储 (使用 Boto3)
        - "minio": MinIO 私有化对象存储 (使用 MinIO SDK)
        - "alioss": 阿里云 OSS (使用 oss2 SDK)
    """

    @staticmethod
    def get_storage_adapter(storage_type: str | None = None) -> StorageAdapter:
        """
        获取存储适配器实例。

        Args:
            storage_type (str, optional): 指定存储类型。如果未提供，默认从配置 (settings.STORAGE_TYPE) 读取。
                有效值：
                - "local": 本地存储
                - "aws" / "s3": AWS S3
                - "minio": MinIO
                - "alioss": 阿里云 OSS

        Returns:
            StorageAdapter: 已初始化的存储适配器实例。

        Raises:
            ValueError: 如果提供了未知的 storage_type。
        """
        stype = (storage_type or settings.STORAGE_TYPE).lower()
        
        if stype == "local":
            return LocalAdapter(settings.STORAGE_LOCAL_ROOT)
        elif stype == "aws" or stype == "s3":
            return AWSS3Adapter()
        elif stype == "minio":
            return MinioAdapter()
        elif stype == "alioss":
            return AliOSSAdapter()
        else:
            raise ValueError(f"未知的存储类型配置: {stype}。支持的类型: local, aws, minio, alioss")

# 全局单例实例，供业务模块直接导入使用
storage = StorageFactory.get_storage_adapter()
