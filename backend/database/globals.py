import os
from dotenv import load_dotenv

load_dotenv()

# PostgreSQL connection string, e.g.:
# postgresql://user:password@host:5432/dbname
# Set DATABASE_URL in your .env file or environment.
DATABASE_URL: str = os.environ["DATABASE_URL"]
