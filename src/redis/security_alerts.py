# -----------------------------------------------------------------------------
# Module: security_alerts.py
# Purpose: Acts as a real-time monitor pub/sub for security alerts arriving concurrently from different booths.
# -----------------------------------------------------------------------------
import json
from config.redis_clients import get_cloud_redis

def main():
    r_cloud = get_cloud_redis()
    pubsub = r_cloud.pubsub()
    pubsub.subscribe("alerts:security_breach")
    print("Waiting for Security breaches...")
    try: 
        for message in pubsub.listen():
            if message["type"] == "message":
                data = message["data"]
                alert_data = json.loads(data)
                print("\n" + "=" * 40)
                print(f"   SECURITY BREACH DETECTED — IMMEDIATE ARREST ORDER")
                print("=" * 40)
                print(f"PASSENGER : {alert_data['full_name'].upper()} ({alert_data['passport_number']})")
                print(f"TICKET    : {alert_data['ticket_number']} | Booth: {alert_data['booth_id']}")
                print(f"STATUS    : {alert_data['status']}")
                print(f"REASON    : {alert_data['reason']}")
                print(f"TIME      : {alert_data['timestamp']}")
                print("=" * 40)
                print(f"Proceed immediately to {alert_data['booth_id']} for arrest.")
                print("=" * 40 + "\n")
    except KeyboardInterrupt:
        print("\nEnding Pub/Sub")

if __name__ == "__main__":
    main()