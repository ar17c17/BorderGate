import json
import os
import sys
import time
from datetime import datetime, timezone
from config.redis_clients import get_cloud_redis, get_local_redis
from src.evaluator import evaluate_passenger
# Set target booth ID for this worker process (fallback to BOX-001)
BOOTH_ID = os.getenv("BOOTH_ID", sys.argv[1] if len(sys.argv) > 1 else "BOX-001")


def start_consumer():
    # Initialize connection clients for Local Docker Redis and Redis Cloud
    r_local = get_local_redis()
    r_cloud = get_cloud_redis()

    # Define dedicated streaming queues for this booth
    pending_queue = f"queue:passengers:{BOOTH_ID}"
    processing_queue = f"queue:passengers:processing:{BOOTH_ID}"
    secondary_priority_queue = "queue:secondary_review:ranking"

    print("=" * 50)
    print(f"BORDERGATE: BOOTH ID: {BOOTH_ID}")
    print("=" * 50)

    processed_count = 0
    accepted = 0
    denied = 0
    secondary = 0

    # Retrieve assigned officer session metadata from Redis Cloud
    agent_badge = r_cloud.get(f"cabin:active:{BOOTH_ID}")
    if agent_badge:
        agent_info = r_cloud.hgetall(f"session:agent:{agent_badge}")
        agent_name = agent_info.get("first_name")
        agent_surname = agent_info.get("last_name")
        agent_rank = agent_info.get("rank")
        print(f"Officer on Duty: {agent_rank} {agent_name} {agent_surname} (#{agent_badge})")


    print("=" * 50)
    err_count = 0

    while True:
        # Atomically pop passenger event from pending queue and push to local processing queue
        event = r_local.blmove(
            pending_queue,
            processing_queue,
            timeout=3,
            src="RIGHT",  # RPOP (FIFO)
            dest="LEFT"   # LPUSH
        )

        if not event:
            print(f"[{BOOTH_ID}] Queue empty. Waiting for passengers...")
            err_count +=1
            if err_count == 5:
                print(f"[{BOOTH_ID}] Queue empty. Closing booth")
                break
            continue

        err_count = 0

        # Deserialize passenger  JSON
        passenger = json.loads(event)
        passport = passenger["passport_number"]
        full_name = passenger["full_name"]
        booth_id = passenger["booth_id"]
        ticket_number = passenger["ticket_number"]
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

        print(f"[{timestamp}] [{BOOTH_ID}] Ticket #{ticket_number}: {full_name} ({passport})")

        # EVALUATION LOGIC
        time.sleep(0.5)  
        decision = evaluate_passenger(passenger, r_cloud)
        status = decision["status"]
        action = decision["action"]
        reason = decision['reason']
        priority = decision.get("priority", 0)

        if status == "APPROVED":
            print(f"[GATE OPENED] {reason}\n")
            accepted += 1
        elif  "DENIED" in status:
            print(f"[XXX-SECURITY ALERT-XXX] {reason}, Action: {action}\n")
            alert = {
                "timestamp": timestamp,
                "booth_id": BOOTH_ID,
                "officer_badge": agent_badge,
                "ticket_number": ticket_number,
                "passport_number": passport,
                "full_name": full_name,
                "status": status,
                "reason": reason,
                "action": action}
            r_cloud.publish("alerts:security_breach", json.dumps(alert))
            denied +=1
        elif status == "SECONDARY_INSPECTION":
            print(f"[SECONDARY REVIEW] {reason}, Action: {action}\n")
            r_local.zadd(secondary_priority_queue, {event: priority})
            secondary +=1

        else:
            print(f"[{status}] {reason}\n")




        # LOGS
        date = timestamp[:10] # Only YYYY/MM/DD
        logs_key = f"log:{date}:{ticket_number}"
        log = {
            "timestamp": timestamp,
            "booth_id": BOOTH_ID,
            "officer_badge": agent_badge,
            "ticket_number": ticket_number,
            "passport_number": passport,
            "full_name": full_name,
            "status": status,
            "gate_action": action,
            "reason": reason
        }
        log = {k: ("" if v is None else str(v)) for k, v in log.items()}
        logs_key = f"log:{timestamp[:10]}:{ticket_number}"
        r_local.hset(logs_key,mapping=log)
        r_local.expire(logs_key,604800) # 7 Day TTL
        r_local.lrem(processing_queue, 1, event)
        processed_count += 1
        time.sleep(1)
    print(f"Total Passengers processed: {processed_count}, Accepted: {accepted}, Denied: {denied}, Secondary Inspection: {secondary}")


if __name__ == "__main__":
    start_consumer()