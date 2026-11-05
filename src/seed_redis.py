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
#  REDIS CLOUD INGESTION (Global Cache, Blacklists & Active Sessions)
# =============================================================================
def seed_cloud(r_cloud):
    print('Initiating dataset ingestion into REDIS CLOUD')

    # -------------------------------------------------------------------------
    # 1.1 Stolen Passports List (SET + HASH)
    # -------------------------------------------------------------------------
    stolen_file = SEED_DIR / 'cloud_stolen_passports.csv'
    if stolen_file.exists():
        with open(stolen_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Limpiar clave de tipo SET
            r_cloud.delete('blacklist:stolen_passports')
            count = 0
            pipe = r_cloud.pipeline()
            for row in reader:
                passport = row['passport_number'].strip()
                # 1. Indexar pasaporte en el SET global
                pipe.sadd('blacklist:stolen_passports', passport)
                # 2. Guardar ficha completa del robo en un HASH
                pipe.hset(f'stolen:{passport}', mapping=row)
                count += 1
            pipe.execute()
            print(f"Loaded {count} stolen passports into SET 'blacklist:stolen_passports' and HASHES 'stolen:*'")

    # -------------------------------------------------------------------------
    #  Wanted People List (ZSET + HASH)
    # -------------------------------------------------------------------------
    wanted_file = SEED_DIR / 'cloud_wanted_persons.csv'
    if wanted_file.exists():
        with open(wanted_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # Limpiar únicamente el ZSET de personas buscadas (removido el delete accidental de stolen)
            r_cloud.delete('blacklist:wanted_persons')

            count = 0
            pipe = r_cloud.pipeline()
            threat_scores = {
                'Critical': 4,
                'High': 3,
                'Medium': 2,
                'Low': 1
            }
            for row in reader:
                passport = row['passport_number'].strip()
                threat_level = row.get('threat_level', 'Low').strip()
                score = threat_scores.get(threat_level, 1)

                # Guardar ficha completa en un HASH
                pipe.hset(f"wanted:{passport}", mapping=row)
                # Indexar en el ZSET ordenado por peligrosidad
                pipe.zadd('blacklist:wanted_persons', {passport: score})
                count += 1
                
            pipe.execute()
            print(f"Loaded {count} wanted individuals into ZSET 'blacklist:wanted_persons' and HASHES 'wanted:*'")

    # -------------------------------------------------------------------------
    #  Visa Entry Policies (HASH per country)
    # -------------------------------------------------------------------------
    visa_file = SEED_DIR / 'cloud_visa_policies.csv'
    if visa_file.exists():
        with open(visa_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            pipe = r_cloud.pipeline()
            for row in reader:
                country = row['country_code'].strip()
                key = f'policy:visa:{country}'
                # Limpiar la clave individual antes de poblar el HASH
                pipe.delete(key)
                pipe.hset(key, mapping=row)
                count += 1
            pipe.execute()
            print(f"Loaded {count} visa policy rules into HASHES 'policy:visa:*'")

    
    # -------------------------------------------------------------------------
    #  Active Agent Sessions (HASH with TTL + Secondary Lookup Index)
    # -------------------------------------------------------------------------
    sessions_file = SEED_DIR / 'cloud_agent_sessions.csv'
    if sessions_file.exists():
        with open(sessions_file, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            count = 0
            pipe = r_cloud.pipeline()

            for row in reader:
                badge_number = row['badge_number'].strip()
                ttl = int(row.pop('ttl_seconds', 28800))
                session_key = f'session:agent:{badge_number}'
                
                pipe.delete(session_key)
                pipe.hset(session_key, mapping=row)
                pipe.expire(session_key, ttl)

                booth_id = row.get('booth_id')
                if booth_id:
                    cabin_key = f'cabin:active:{booth_id}'
                    pipe.delete(cabin_key)
                    pipe.set(cabin_key, badge_number, ex=ttl)

                count += 1

            pipe.execute()
            print(f"Initialized {count} active officer sessions into HASHes 'session:agent:*' and secondary indexes 'cabin:active:*'")


# =============================================================================
#  LOCAL DOCKER REDIS INGESTION (Real-Time Passenger Buffer / Queue)
# =============================================================================
def seed_local(r_local):
    print('\nInitiating dataset ingestion into LOCAL REDIS (Docker) ---')

    queue_file = SEED_DIR / 'docker_passenger_queue.csv'
    if not queue_file.exists():
        print('WARNING: Passenger queue dataset not found in data/seed_data/.')
        return

    with open(queue_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        rows = list(reader)

        booths = {row['booth_id'].strip() for row in rows if 'booth_id' in row}

        for booth in booths:
            r_local.delete(f'queue:passengers:{booth}')
            r_local.delete(f'queue:passengers:processing:{booth}')

        r_local.delete('queue:passengers:pending')

        count = 0
        pipe = r_local.pipeline()
        for row in rows:
            booth_id = row['booth_id'].strip()

            if 'biometric_match_score' in row:
                row['biometric_match_score'] = float(row['biometric_match_score'])
            if 'nfc_valid' in row:
                row['nfc_valid'] = row['nfc_valid'].lower() == 'true'

            pipe.rpush(f'queue:passengers:{booth_id}', json.dumps(row))
            count += 1

        pipe.execute()
        print(f"Pushed {count} passenger events across {len(booths)} booth queues ('queue:passengers:BOX-*')")
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