import uvicorn
from dotenv import load_dotenv

load_dotenv()

from config import settings

if __name__ == "__main__":
    uvicorn.run("app:app", host="0.0.0.0", log_level=settings.LOG_LEVEL)
