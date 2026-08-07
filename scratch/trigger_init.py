import os
import sys

sys.path.append(os.path.abspath(os.path.dirname(__file__)))

from app import create_app
app = create_app()

print("App created and init_db triggered successfully!")
