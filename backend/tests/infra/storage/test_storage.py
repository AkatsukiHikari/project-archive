import io
import pytest
from unittest.mock import MagicMock
from app.infra.storage.local import LocalAdapter
from app.infra.storage.minio_storage import MinioAdapter
from app.infra.storage.aws_s3 import AWSS3Adapter
from app.infra.storage.alioss import AliOSSAdapter

def test_local_storage(tmp_path):
    """
    Unit Test for LocalAdapter (Real File System)
    Using tmp_path fixture from pytest
    """
    # Initialize with a temp directory
    adapter = LocalAdapter(root_dir=str(tmp_path))
    bucket = "test-bucket"
    filename = "test-file.txt"
    content = b"Hello Local Storage"
    f = io.BytesIO(content)
    
    # 1. Test Save
    # Should return absolute path string
    saved_path = adapter.save(f, filename, bucket, "text/plain")
    assert filename in saved_path
    assert bucket in saved_path
    
    # Verify file content on disk
    with open(saved_path, "rb") as verify_f:
        assert verify_f.read() == content
    
    # 2. Test Exists
    assert adapter.exists(filename, bucket) is True
    
    # 3. Test Delete
    result = adapter.delete(filename, bucket)
    assert result is True
    assert adapter.exists(filename, bucket) is False

def test_minio_storage_mocked(mocker):
    """
    Unit Test for MinioAdapter (Mocked MinIO Client)
    """
    # Mock the Minio class in the minio_storage module
    mock_minio_cls = mocker.patch("app.infra.storage.minio_storage.Minio")
    mock_client = mock_minio_cls.return_value
    
    # Mock settings to avoid connection errors during init
    mocker.patch("app.infra.storage.minio_storage.settings.MINIO_ENDPOINT", "localhost:9000")
    mocker.patch("app.infra.storage.minio_storage.settings.MINIO_ACCESS_KEY", "minio")
    mocker.patch("app.infra.storage.minio_storage.settings.MINIO_SECRET_KEY", "minio123")
    
    adapter = MinioAdapter()
    bucket = "minio-bucket"
    filename = "minio-file.txt"
    content = b"Hello MinIO"
    f = io.BytesIO(content)
    
    # 1. Test Save
    adapter.save(f, filename, bucket)
    
    # Verify put_object was called with correct args
    mock_client.put_object.assert_called_once()
    call_args = mock_client.put_object.call_args
    assert call_args[1]['bucket_name'] == bucket
    assert call_args[1]['object_name'] == filename
    
    # 2. Test Presigned URL
    mock_client.get_presigned_url.return_value = "http://mock-minio/signed-url"
    url = adapter.get_presigned_url(filename, bucket)
    assert url == "http://mock-minio/signed-url"

def test_aws_s3_storage_mocked(mocker):
    """
    Unit Test for AWSS3Adapter (Mocked Boto3)
    """
    # Mock boto3.client
    mock_boto3 = mocker.patch("app.infra.storage.aws_s3.boto3.client")
    mock_s3_client = mock_boto3.return_value
    
    # Mock settings
    mocker.patch("app.infra.storage.aws_s3.settings.AWS_ACCESS_KEY_ID", "fake-id")
    mocker.patch("app.infra.storage.aws_s3.settings.AWS_SECRET_ACCESS_KEY", "fake-secret")
    mocker.patch("app.infra.storage.aws_s3.settings.AWS_REGION", "us-east-1")
    
    adapter = AWSS3Adapter()
    bucket = "aws-bucket"
    filename = "aws-file.txt"
    content = b"Hello AWS"
    f = io.BytesIO(content)
    
    # 1. Test Save (upload_fileobj)
    adapter.save(f, filename, bucket)
    mock_s3_client.upload_fileobj.assert_called_once()
    args, kwargs = mock_s3_client.upload_fileobj.call_args
    assert args[1] == bucket
    assert args[2] == filename
    
    # 2. Test Presigned URL (generate_presigned_url)
    mock_s3_client.generate_presigned_url.return_value = "http://mock-aws/signed-url"
    url = adapter.get_presigned_url(filename, bucket)
    assert url == "http://mock-aws/signed-url"

def test_alioss_storage_mocked(mocker):
    """
    Unit Test for AliOSSAdapter (Mocked oss2)
    """
    # Mock oss2 library in alioss module
    mocker.patch("app.infra.storage.alioss.oss2.Auth")
    mock_bucket_cls = mocker.patch("app.infra.storage.alioss.oss2.Bucket")
    mock_bucket_instance = mock_bucket_cls.return_value
    
    # Mock settings
    mocker.patch("app.infra.storage.alioss.settings.OSS_ACCESS_KEY_ID", "ali-id")
    mocker.patch("app.infra.storage.alioss.settings.OSS_ACCESS_KEY_SECRET", "ali-secret")
    mocker.patch("app.infra.storage.alioss.settings.OSS_ENDPOINT", "oss-cn-hangzhou.aliyuncs.com")
    
    adapter = AliOSSAdapter()
    bucket = "ali-bucket"
    filename = "ali-file.txt"
    content = b"Hello OSS"
    f = io.BytesIO(content)
    
    # 1. Test Save
    adapter.save(f, filename, bucket)
    
    # Verify put_object was called
    mock_bucket_instance.put_object.assert_called_once()
    args, _ = mock_bucket_instance.put_object.call_args
    assert args[0] == filename
    
    # 2. Test Delete
    adapter.delete(filename, bucket)
    mock_bucket_instance.delete_object.assert_called_once_with(filename)
