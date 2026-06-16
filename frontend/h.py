import os
from dotenv import load_dotenv
load_dotenv() 
BACKEND_URL: str = os.getenv("BACKEND_URL", "http://backend:8000")
print(BACKEND_URL)