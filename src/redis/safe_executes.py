# -----------------------------------------------------------------------------
# Module: safe_executes.py
# Purpose: Checks the user permissions to decide wether it can be performed or not.
# -----------------------------------------------------------------------------
import json
from redis.exceptions import NoPermissionError, RedisError
def safe_publish(r, channel, payload):
        try:
            r.publish(channel, json.dumps(payload))
            return True
        except NoPermissionError as err:
            print(f"[WARN] Permission denied: cannot publish to '{channel}'")
        return False

def safe_execute(pipe, operation="pipeline"):
    try:
        return pipe.execute()
    except NoPermissionError as err:
        print(f"[WARN] Permission denied in {operation}")
        return False
    except RedisError as err:
        print(f"[ERROR] Redis error in {operation}")
        return False

def safe_delete(r, key):
    try:
        return r.delete(key)
    except NoPermissionError as err:
        print(f"[WARN] Permission denied: cannot delete '{key}'")
        return False
    except RedisError as err:
        print(f"[ERROR] Redis delete failed for '{key}'")
        return False