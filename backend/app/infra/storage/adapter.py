from abc import ABC, abstractmethod
from typing import BinaryIO


class StorageAdapter(ABC):
    """
    统一对象存储适配器抽象基类。

    约定：
        - save()             — 写入文件，返回对象键（object key）
        - get_public_url()   — 构造永久可公开访问的 URL（适用于头像、缩略图等公共资源）
        - get_presigned_url()— 生成有时效的临时 URL（适用于私有档案资源，如机密文件）
        - delete()           — 删除对象
        - exists()           — 检查对象是否存在

    公共资源 vs 私有资源：
        公共资源（avatars / thumbnails）：上传后调 get_public_url() 把永久 URL 存入 DB，随取随用。
        私有资源（archives / attachments）：存 object key，访问时调 get_presigned_url() 临时授权。
    """

    @abstractmethod
    def save(self, file_object: BinaryIO, filename: str, bucket: str, content_type: str = "application/octet-stream") -> str:
        """
        保存文件到对象存储。

        Returns:
            str: 保存成功后的对象键（filename）。
        """

    @abstractmethod
    def get_public_url(self, filename: str, bucket: str) -> str:
        """
        构造文件的永久公开访问 URL。

        适用于 avatars、thumbnails 等公共读取资源，上传后直接把此 URL 存入数据库。
        各适配器根据自身服务规则构造：
            - Local  : /static/{bucket}/{filename}
            - MinIO  : {MINIO_PUBLIC_URL}/{bucket}/{filename}
            - AWS S3 : https://{bucket}.s3.{region}.amazonaws.com/{filename}
            - AliOSS : https://{bucket}.{endpoint}/{filename}

        Args:
            filename (str): 对象键（上传时使用的 filename）。
            bucket   (str): 存储桶名称。

        Returns:
            str: 永久可访问的公开 URL，可直接存入数据库。
        """

    @abstractmethod
    def get_presigned_url(self, filename: str, bucket: str, expires_seconds: int = 3600) -> str:
        """
        生成有时效的临时访问 URL（预签名 URL）。

        适用于私有存储桶中的档案、附件等需要鉴权的资源。

        Args:
            filename        (str): 对象键。
            bucket          (str): 存储桶名称。
            expires_seconds (int): 链接有效期（秒）。默认 3600。

        Returns:
            str: 带签名的临时 HTTP(S) URL。
        """

    @abstractmethod
    def delete(self, filename: str, bucket: str) -> bool:
        """删除指定对象。成功返回 True，失败返回 False。"""

    @abstractmethod
    def exists(self, filename: str, bucket: str) -> bool:
        """检查对象是否存在。存在返回 True，不存在返回 False。"""
