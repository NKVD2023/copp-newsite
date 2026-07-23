import app
from io import BytesIO
import os

png_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'

class DummyFile:
    def __init__(self, filename):
        self.filename = filename
        self.stream = BytesIO(png_data)
    def save(self, path):
        pass

application = app.create_app()
with application.app_context():
    from app.utils.image_utils import save_image_as_webp
    f = DummyFile("Фотография.png")
    res = save_image_as_webp(f, "test_upload", add_uuid=True)
    print("Resulting filename:", res)
