import os
import redis
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

REDIS_LOCAL_HOST = os.getenv("REDIS_LOCAL_HOST", "localhost")
REDIS_LOCAL_PORT = int(os.getenv("REDIS_LOCAL_PORT", 6379))

REDIS_CLOUD_HOST = os.getenv("REDIS_CLOUD_HOST", None)
REDIS_CLOUD_PORT = int(os.getenv("REDIS_CLOUD_PORT", 6380))
REDIS_CLOUD_USER = os.getenv("REDIS_CLOUD_USER", None)
REDIS_CLOUD_PASSWORD = os.getenv("REDIS_CLOUD_PASSWORD", None)


def get_local_redis():
    r = redis.Redis(
        host=REDIS_LOCAL_HOST,
        port=REDIS_LOCAL_PORT,
        db=0,
        decode_responses=True,
    )
    try:
        r.ping() 
    except redis.ConnectionError:
        raise ConnectionError(
            f"Could not connect to the local Redis instance at {REDIS_LOCAL_HOST}:{REDIS_LOCAL_PORT}."
        )
    return r


def get_cloud_redis():
    if not REDIS_CLOUD_HOST or not REDIS_CLOUD_PASSWORD:
        raise ValueError("Missing Redis Cloud credentials at .env")
    r = redis.Redis(
        host=REDIS_CLOUD_HOST,
        port=REDIS_CLOUD_PORT,
        username=REDIS_CLOUD_USER,
        password=REDIS_CLOUD_PASSWORD,
        decode_responses=True,
    )
    try:
        r.ping() 
    except redis.ConnectionError:
        raise ConnectionError(
            f"Could not connect to the Cloud Redis instance at {REDIS_CLOUD_HOST}:{REDIS_CLOUD_PORT}."
        )
    return r