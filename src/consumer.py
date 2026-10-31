from datetime import datetime, timezone
import json
import time
from config.redis_clients import get_cloud_redis, get_local_redis


def start_consumer():
    r_local = get_local_redis()
    r_cloud = get_cloud_redis()

    # Streaming queues
    pending_queue = "queue:passengers:pending"
    processing_queue = "queue:passengers:processing"
    secondary_priority_queue = "queue:secondary_review:ranking"

    print("=" * 40)
    print("BORDERGATE: STREAMING CONSUMER READY")
    print("=" * 40)

    processed_count = 0


    while True:

        event = r_local.blmove(
            first_list=pending_queue,
            second_list=processing_queue,
            timeout=5,
            src="RIGHT",
            dest="LEFT"
        )


        if not event:
            print("Waiting for passengers in pending queue")
            time.sleep(2)
            continue


        passenger = json.loads(event)
        passport = passenger["passport_number"]
        full_name = passenger["full_name"]
        booth_id = passenger["booth_id"]
        
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        


