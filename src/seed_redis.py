import csv
import json
from pathlib import Path
from config.redis_clients import get_cloud_redis, get_local_redis

# =============================================================================
# PATH CONFIGURATION
# =============================================================================
BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / 'data' / 'seed_data'


# =============================================================================
# 1. REDIS CLOUD INGESTION (Global Cache, Blacklists & Active Sessions)
# =============================================================================
def seed_cloud(r_cloud):
    print('Initiating dataset ingestion into REDIS CLOUD')

    # 1.1 Stolen Passports List (SET)
    stolen_file = SEED_DIR / 'cloud_stolen_passports.csv'

    if stolen_file.exists():
        with open(stolen_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            pipe = r_cloud.pipeline()
            for row in reader:
                # Extract passport/document identifier
                doc = list(row.values())[0].strip()
                pipe.sadd('blacklist:stolen_passports', doc)
                count += 1
            pipe.execute()
            print(f"Loaded {count} stolen passports into SET 'blacklist:stolen_passports'")


    # 1.2 Wanted People List (SET)
    wanted_file = SEED_DIR / 'cloud_wanted_persons.csv'
    if wanted_file.exists():
        with open(wanted_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            pipe = r_cloud.pipeline()
            for row in reader:
                # Extract person/document identifier
                person = list(row.values())[0].strip()
                pipe.sadd('blacklist:wanted_persons', person)
                count += 1
            pipe.execute()
            print(f"Loaded {count} wanted individuals into SET 'blacklist:wanted_persons'")

    
    # 1.3 Visa Entry Policies (HASH)
    visa_file = SEED_DIR / 'cloud_visa_policies.csv'
    if visa_file.exists():
        with open(visa_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            pipe = r_cloud.pipeline()
            for row in reader:
                country = row['codigo_pais']
                pipe.hset(f'policy:visa:{country}', mapping=row)
                count += 1
            pipe.execute()
            print(f"Loaded {count} visa policy rules into HASH 'policy:visa:*'")



    # 1.4 Daily Flights Cache (HASH with 24-hour TTL)
    flights_file = SEED_DIR / 'cloud_daily_flights.csv'
    if flights_file.exists():
        with open(flights_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            pipe = r_cloud.pipeline()
            for row in reader:
                flight_id = row['codigo_vuelo']
                key = f'flight:{flight_id}'
                pipe.hset(key, mapping=row)
                # Expire after 24 hours (86400 seconds)
                pipe.expire(key, 86400)
                count += 1
            pipe.execute()
            print(f"Cached {count} daily flight schedules into HASHes 'flight:*' (TTL: 24h)")



    # 1.5 Active Agent Sessions (HASH with TTL)
    sessions_file = SEED_DIR / 'cloud_agent_sessions.csv'
    if sessions_file.exists():
        with open(sessions_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            pipe = r_cloud.pipeline()
            for row in reader:
                badge_number = row['num_placa']
                ttl = int(row.get('ttl_segundos', 28800))
                session_key = f'session:agent:{badge_number}'

                # Store session metadata
                session_data = {
                    'nombre_agente': row.get('nombre_agente', ''),
                    'rango': row.get('rango', ''),
                    'cabina_asignada': row.get('cabina_asignada', ''),
                    'turno': row.get('turno', ''),
                    'permisos': row.get('permisos', ''),
                }
                pipe.hset(session_key, mapping=session_data)
                pipe.expire(session_key, ttl)

                # Secondary lookup index: map gate/cabin to active badge number
                cabin = row.get('cabina_asignada')
                if cabin:
                    pipe.set(f'cabin:active:{cabin}', badge_number, ex=ttl)

                count += 1
            pipe.execute()
            print(f"Initialized {count} active officer sessions into HASHes 'session:agent:*' with TTL")


# =============================================================================
# 2. LOCAL DOCKER REDIS INGESTION (Real-Time Passenger Buffer / Queue)
# =============================================================================
def seed_local(r_local):
    
    print('\nInitiating dataset ingestion into LOCAL REDIS (Docker) ---')

    queue_files = list(SEED_DIR.glob('docker_passenger_queue.csv'))
    if not queue_files:
        print('WARNING: Passenger queue dataset not found in data/seed_data/.')
        return

    queue_file = queue_files[0]
    with open(queue_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)

        # Clear existing queue buffer to maintain deterministic execution
        r_local.delete('queue:passengers:pending')

        count = 0
        pipe = r_local.pipeline()
        for row in reader:
            # Enqueue raw record serialized as a JSON string
            pipe.rpush('queue:passengers:pending', json.dumps(row))
            count += 1
        pipe.execute()
        print(f"Pushed {count} passenger events into LIST 'queue:passengers:pending'")


# =============================================================================
# MAIN INGESTION ENTRY POINT
# =============================================================================
if __name__ == '__main__':
    try:
        print('[INIT] Establishing connection to Redis instances...')
        r_loc = get_local_redis()
        r_cld = get_cloud_redis()

        # Execute ingestion routines
        seed_cloud(r_cld)
        seed_local(r_loc)

        print('\nAll datasets successfully loaded into Redis.')

    except Exception as err:
        print(f'\nERROR: Seeding process failed: {err}')
    