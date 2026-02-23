import shutil
from pathlib import Path
from typing import BinaryIO
from app.core.config import settings
from app.infra.storage.adapter import StorageAdapter

class LocalAdapter(StorageAdapter):
    """
    本地文件系统适配器。
    
    使用场景：
        仅用于本地开发环境或非云部署场景。
        数据直接保存到宿主机的指定目录中。

    Attributes:
        root_dir (Path): 存储的根目录路径。
    """
    
    def __init__(self, root_dir: str = "/tmp/sams_storage"):
        """
        初始化本地存储适配器。

        Args:
            root_dir (str, optional): 数据根目录。如果不存在将自动创建。默认为 "/tmp/sams_storage"。
        """
        self.root_dir = Path(root_dir)
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _get_path(self, bucket: str, filename: str) -> Path:
        """
        内部辅助方法：构建文件的绝对路径。

        Args:
            bucket (str): 存储桶（这里模拟为子目录）。
            filename (str): 文件名。

        Returns:
            Path: 文件在本地磁盘上的完整路径。
        """
        return self.root_dir / bucket / filename

    def save(self, file_object: BinaryIO, filename: str, bucket: str, content_type: str = "application/octet-stream") -> str:
        """
        保存文件到本地磁盘。

        逻辑：
        1. 确保目标目录存在（使用 bucket 作为子目录）。
        2. 重置文件指针。
        3. 使用 shutil 高效复制流数据。

        Returns:
            str: 文件的绝对存储路径。
        """
        target_dir = self.root_dir / bucket
        target_dir.mkdir(parents=True, exist_ok=True)
        target_path = target_dir / filename
        
        # 重置文件指针以确保完整读取
        file_object.seek(0)
        
        with open(target_path, "wb") as f:
            shutil.copyfileobj(file_object, f)
            
        return str(target_path)

    def get_presigned_url(self, filename: str, bucket: str, expires_seconds: int = 3600) -> str:
        """
        生成伪预签名链接。
        
        注意：
            在生产环境（通常由 Nginx 代理）中，这应该返回静态资源的 URL。
            但在本地开发模式下，我们模拟为 `/static/bucket/filename` 格式。

        Returns:
            str: 文件的相对访问路径。
        """
        return f"/static/{bucket}/{filename}"

    def delete(self, filename: str, bucket: str) -> bool:
        """
        删除本地文件。

        Returns:
            bool: 文件被删除返回 True，文件不存在也返回 False（符合幂等性预期，但此处实现返回 False）。
        """
        path = self._get_path(bucket, filename)
        if path.exists():
            path.unlink()
            return True
        return False

    def exists(self, filename: str, bucket: str) -> bool:
        """
        检查本地文件是否存在。

        Returns:
            bool: 存在 True，反之 False。
        """
        return self._get_path(bucket, filename).exists()