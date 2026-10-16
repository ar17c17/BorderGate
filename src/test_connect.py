from config.redis_clients import get_cloud_redis, get_local_redis

print("--- Checking Redis connection ---\n")

try:
    r_local = get_local_redis()
    print(
        f"Local Redis connection SUCCESSFUL (Docker). PING -> {r_local.ping()}"
    )
except Exception as err:
    print(f"Local Redis connection failed: {err}")

try:
    r_cloud = get_cloud_redis()
    print(
        f"Cloud Redis connection SUCCESSFUL (Redis Cloud). PING -> {r_cloud.ping()}"
    )
except Exception as err:
    print(f"Cloud Redis connection failed: {err}")