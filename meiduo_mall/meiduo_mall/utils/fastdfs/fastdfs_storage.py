from django.conf import settings
from django.core.files.storage import Storage
from fdfs_client.client import Fdfs_client


class FastDFSStorage(Storage):

    def save(self, name, content, max_length=None):

        client = Fdfs_client(settings.FDFS_CLIENT_CONF)

        result = client.upload_by_buffer(content.read())

        if result.get('Status') != 'Upload successed.':

            raise Exception('上传文件到FDFS系统失败')

        file_id = result.get('Remote file_id')

        return file_id

    def exists(self, name):

        return False

    def url(self, name):

        return settings.FDFS_URL + name
