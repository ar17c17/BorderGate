import json
from config.redis_clients import get_cloud_redis, get_local_redis
import time
from datetime import datetime, timezone
def main():
    r_local = get_local_redis()
    r_cloud = get_cloud_redis()
    secondary_queue = "queue:secondary_review:ranking"
    print("=" * 40)
    print(" BORDERGATE: SECONDARY INSPECTION DESK (SECOND LINE)")
    print(" Waiting for passengers...")
    print("=" * 40)

    try:
        while True:
            result = r_local.zpopmax(secondary_queue)
            if not result:
                time.sleep(2)
                continue
            event, priority_score = result[0]
            event_str = event.decode("utf-8") if isinstance(event, bytes) else event
            passenger = json.loads(event_str)


            print("=" * 40)
            print(f"   SECONDARY REVIEW — PRIORITY SCORE: {priority_score:.1f}")
            print("=" * 40)
            print(f" PASSENGER : {passenger['full_name']} ({passenger['passport_number']})")
            print(f" TICKET    : {passenger['ticket_number']} | Booth: {passenger['booth_id']}")
            print(f" BIOMETRIC : Score: {passenger['biometric_match_score']} | NFC Valid: {passenger['nfc_valid']}")
            print("=" * 40 + "\n")
            time.sleep(1)
            
            now_utc = datetime.now(timezone.utc)
            timestamp_str = now_utc.strftime("%Y-%m-%d %H:%M:%S")
            date_prefix = now_utc.strftime("%Y-%m-%d")

            if passenger['nfc_valid'] or float(passenger['biometric_match_score']) >= 0.6:
                resolution = "RESOLVED_APPROVED"
                action = "SECONDARY_CLEARANCE_GRANTED"
                print(f"DECISION  : {resolution} — {action}")
            else:
                resolution = "RESOLVED_DENIED"
                action = "REFUSED_ENTRY_SECONDARY"
                print(f"DECISION  : {resolution} — {action}")
                
                alert_payload = {
                    "timestamp": timestamp_str,
                    "officer": "INSPECTOR-2ND-LINE",
                    "ticket_number": passenger['ticket_number'],
                    "passport_number": passenger['passport_number'],
                    "full_name": passenger['full_name'],
                    "status": resolution,
                    "reason": "Failed  secondary inspection",
                    "action": action
                }
                r_cloud.publish("alerts:security_breach", json.dumps(alert_payload))

            audit_key = f"log:{date_prefix}:{passenger['ticket_number']}"
            r_local.hset(audit_key, mapping={
                "secondary_resolution": resolution,
                "secondary_action": action,
                "secondary_timestamp": timestamp_str
            })

            print("=" * 40 + "\n")
            time.sleep(3)

    except KeyboardInterrupt:
        print("\nSecondary Inspection monitor closed.")

if __name__ == "__main__":
    main()