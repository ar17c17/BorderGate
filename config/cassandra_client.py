# -----------------------------------------------------------------------------
# Module: cassandra_clients.py
# Purpose: Gets from the .env the needed information to start Cassandra client.
# -----------------------------------------------------------------------------
import os
from pathlib import Path
from dotenv import load_dotenv
from cassandra.cluster import Cluster, ExecutionProfile, EXEC_PROFILE_DEFAULT, NoHostAvailable
from cassandra.policies import DCAwareRoundRobinPolicy, TokenAwarePolicy
from cassandra import ConsistencyLevel

BASE_DIR = Path(__file__).resolve().parent.parent
ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH,override=True)

CASSANDRA_HOST = os.getenv("CASSANDRA_HOST", "localhost")
CASSANDRA_PORT = int(os.getenv("CASSANDRA_PORT", 9042))
CASSANDRA_KEYSPACE = os.getenv("CASSANDRA_KEYSPACE", None)
CASSANDRA_LOCAL_DC = os.getenv("CASSANDRA_LOCAL_DC", None)

def get_cassandra_session():
    if not CASSANDRA_KEYSPACE or not CASSANDRA_LOCAL_DC:
        raise ValueError("Missing Cassandra settings at .env")
    
    profile = ExecutionProfile(
        load_balancing_policy=TokenAwarePolicy(DCAwareRoundRobinPolicy(local_dc=CASSANDRA_LOCAL_DC)), 
        consistency_level=ConsistencyLevel.LOCAL_QUORUM
    )

    cluster = Cluster(
        contact_points=[CASSANDRA_HOST], 
        port=CASSANDRA_PORT, 
        execution_profiles={
            EXEC_PROFILE_DEFAULT: profile
        }
    )

    try:
        session = cluster.connect(keyspace=CASSANDRA_KEYSPACE)

    except NoHostAvailable as err:
        cluster.shutdown()
        raise ConnectionError(f"Could not connect to Cassandra at {CASSANDRA_HOST}:{CASSANDRA_PORT}") from err

    return cluster, session
