from dotenv import load_dotenv
import os

load_dotenv()

# == Configuration Variables ==
FILE_PATH = os.getenv("FILE_PATH", "/default/path/to/monitor")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///./test.db")
OPEN_API_KEY = os.getenv("OPENAI_API_KEY", "your-default-api-key")