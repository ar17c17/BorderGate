# -----------------------------------------------------------------------------
# Module: test_connect.py
# Purpose: Executes thre connectivy tests.
# -----------------------------------------------------------------------------
from config.cassandra_client import get_cassandra_session
from config.redis_clients import get_cloud_redis, get_local_redis

try:
    r_local = get_local_redis()
    print(f"Local Redis connection SUCCESSFUL (Docker). PING -> {r_local.ping()}")
except Exception as err:
    print(f"Local Redis connection failed: {err}")
try:
    r_cloud = get_cloud_redis()
    print(
        f"Cloud Redis connection SUCCESSFUL (Redis Cloud). PING -> {r_cloud.ping()}"
    )
except Exception as err:
    print(f"Cloud Redis connection failed: {err}")
cluster = None
try:
    cluster, session = get_cassandra_session()
    print(
        f"Cassandra connection SUCCESSFUL (keyspace={session.keyspace}). "
    )
except Exception as err:
    print(f"Cassandra connection failed: {err}")
finally:
    if cluster is not None:
        cluster.shutdown()