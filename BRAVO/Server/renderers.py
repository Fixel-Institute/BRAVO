import json

from rest_framework.renderers import BaseRenderer

class BinaryRenderer(BaseRenderer):
    media_type = 'application/octet-stream'
    format = 'bin'
    charset = None

    def render(self, data, accepted_media_type=None, renderer_context=None):
        if data is None:
            return b''

        if isinstance(data, bytes):
            return data

        if isinstance(data, (bytearray, memoryview)):
            return bytes(data)

        if isinstance(data, str):
            return data.encode('utf-8')

        return json.dumps(data, default=str).encode('utf-8')