from abc import ABC, abstractmethod
from typing import BinaryIO

class StorageAdapter(ABC):
    """
    统一的对象存储适配器接口。
    定义了文件上传、下载链接生成、删除和存在性检查的标准行为。
    """
    
    @abstractmethod
    def save(self, file_object: BinaryIO, filename: str, bucket: str, content_type: str = "application/octet-stream") -> str:
        """
        保存文件到对象存储。

        Args:
            file_object (BinaryIO): 包含文件内容的二进制流对象（需支持 read/seek）。
            filename (str): 在存储桶中保存的目标文件名（对象键）。
            bucket (str): 存储桶名称。
            content_type (str, optional): 文件的 MIME 类型。默认为 "application/octet-stream"。

        Returns:
            str: 保存成功后的文件名（对象键）。
        """
        pass
        
    @abstractmethod
    def get_presigned_url(self, filename: str, bucket: str, expires_seconds: int = 3600) -> str:
        """
        生成文件的临时下载链接（预签名 URL）。

        Args:
            filename (str): 文件名（对象键）。
            bucket (str): 存储桶名称。
            expires_seconds (int, optional): 链接有效期（秒）。默认为 3600 秒（1小时）。

        Returns:
            str: 可直接访问的 HTTP(S) 下载链接。
        """
        pass
        
    @abstractmethod
    def delete(self, filename: str, bucket: str) -> bool:
        """
        删除指定文件。

        Args:
            filename (str): 要删除的文件名（对象键）。
            bucket (str): 存储桶名称。

        Returns:
            bool: 删除成功返回 True，失败返回 False。
        """
        pass
        
    @abstractmethod
    def exists(self, filename: str, bucket: str) -> bool:
        """
        检查文件是否存在。

        Args:
            filename (str): 文件名（对象键）。
            bucket (str): 存储桶名称。

        Returns:
            bool: 存在返回 True，不存在或检查失败返回 False。
        """
        pass
