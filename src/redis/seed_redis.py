# -----------------------------------------------------------------------------
# Module: seed_redis.py
# Purpose: Loads data from seed CSVs and uploads it to the corresponding Redis instance (Cloud or Docker)
# Inputs: --cloud (Cloud only), --local (Docker only), or neither to seed both by default
# -----------------------------------------------------------------------------
import argparse
import csv
import json
from pathlib import Path
from config.redis_clients import get_cloud_redis, get_local_redis
from safe_executes import safe_execute, safe_delete

SEED_DIR = Path(__file__).resolve().parent.parent.parent / 'data' / 'seed_data'


def seed_cloud(r_cloud):
    print('Seeding redis cloud')
    # Stolen passports
    stolen_file = SEED_DIR / 'cloud_stolen_passports.csv'
    if stolen_file.exists():
        with open(stolen_file, encoding='utf-8') as f:
            # Check user permissions to perform the action
            safe_delete(r_cloud, 'blacklist:stolen_passports')
            count = 0
            pipe = r_cloud.pipeline()
            for row in csv.DictReader(f):
                passport = row['passport_number'].strip()
                pipe.sadd('blacklist:stolen_passports', passport)
                pipe.hset(f'stolen:{passport}', mapping=row)
                count += 1
            # Check user permissions to perform the action
            status = safe_execute(pipe, 'Cloud: stolen passports')
            if status:
                print(f'{count} stolen passports')

    # Wanted people
    wanted_file = SEED_DIR / 'cloud_wanted_persons.csv'

    if wanted_file.exists():
        with open(wanted_file, encoding='utf-8') as f:
            # Check user permissions to perform the action
            safe_delete(r_cloud, 'blacklist:wanted_persons')
            count = 0
            pipe = r_cloud.pipeline()
            threat_scores = {'Critical': 4, 'High': 3, 'Medium': 2, 'Low': 1}
            for row in csv.DictReader(f):
                passport = row['passport_number'].strip()
                level = row.get('threat_level', 'Low').strip()
                pipe.hset(f'wanted:{passport}', mapping=row)
                pipe.zadd('blacklist:wanted_persons', {passport: threat_scores.get(level, 1)})
                count += 1
            status = safe_execute(pipe, 'Cloud: wanted persons')
            if status:
                print(f'{count} wanted persons')

    # Visa policies
    visa_file = SEED_DIR / 'cloud_visa_policies.csv'

    if visa_file.exists():
        with open(visa_file, encoding='utf-8') as f:
            count = 0
            pipe = r_cloud.pipeline()
            for row in csv.DictReader(f):
                key = 'policy:visa:' + row['country_code'].strip()
                pipe.delete(key)
                pipe.hset(key, mapping=row)
                count += 1
            # Check user permissions to perform the action
            status = safe_execute(pipe, 'Cloud: visa policies')
            if status:
                print(f'{count} visa policies')

    # Aggents
    agent_sessions = SEED_DIR / 'cloud_agent_sessions.csv'

    if agent_sessions.exists():
        with open(agent_sessions, encoding='utf-8') as f:
            count = 0
            pipe = r_cloud.pipeline()
            for row in csv.DictReader(f):
                badge = row['badge_number'].strip()
                ttl = int(row.pop('ttl_seconds', 28800))
                key = f'session:agent:{badge}'
                pipe.delete(key)
                pipe.hset(key, mapping=row)
                pipe.expire(key, ttl)

                booth = row.get('booth_id')
                if booth:
                    pipe.delete(f'cabin:active:{booth}')
                    pipe.set(f'cabin:active:{booth}', badge, ex=ttl)
                count += 1
            # Check user permissions to perform the action
            status = safe_execute(pipe, 'Cloud: agent sessions')
            if status:
                print(f'{count} agent sessions')


def seed_redis(r_local):
    print('Seeding local redis')

    queue_file = SEED_DIR / 'docker_passenger_queue.csv'
    if not queue_file.exists():
        print('No passenger CSV found')
        return

    with open(queue_file, encoding='utf-8') as f:
        rows = list(csv.DictReader(f))

    booths = {row['booth_id'].strip() for row in rows if 'booth_id' in row}

    for b in booths:
        r_local.delete(f'queue:passengers:{b}')
        r_local.delete(f'queue:passengers:processing:{b}')
        
    r_local.delete('queue:passengers:pending')

    count = 0
    pipe = r_local.pipeline()
    for row in rows:
        if 'biometric_match_score' in row:
            row['biometric_match_score'] = float(row['biometric_match_score'])
        if 'nfc_valid' in row:
            row['nfc_valid'] = row['nfc_valid'].lower() == 'true'
        pipe.rpush(f"queue:passengers:{row['booth_id'].strip()}", json.dumps(row))
        count += 1
    pipe.execute()
    print(f'{count} passengers in {len(booths)} booths')


if __name__ == '__main__':
    # Set arguments logic to select type of seeding
    parser = argparse.ArgumentParser(description='Seed redis cloud and/or local')
    parser.add_argument('--cloud', action='store_true')
    parser.add_argument('--local', action='store_true')
    args = parser.parse_args()

    # Without any args, cloud and redis are added by default
    both = not args.cloud and not args.local

    try:
        if args.local or both:
            seed_redis(get_local_redis())
        if args.cloud or both:
            seed_cloud(get_cloud_redis())
        print('Done')
    except Exception as err:
        print(f'ERROR: {err}')