import csv
import uuid
from datetime import datetime, date, timezone
from pathlib import Path
from cassandra.query import UNSET_VALUE
from config.cassandra_client import get_cassandra_session

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR/'data'/'seed_data'
CSV_PATH = SEED_DIR/'cassandra_border_crossings.csv'

def optional(value, convert):
    if value == "":
        return UNSET_VALUE
    return convert(value)

def parse_ts(text):
    return datetime.strptime(text, "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)

def parse_row(row):
    return {
        "crossing_id": uuid.UUID(row["crossing_id"]),
        "crossing_ts": parse_ts(row["crossing_ts"]),
        "crossing_date": date.fromisoformat(row["crossing_date"]),
        "biometric_match_score": float(row["biometric_match_score"]),
        "nfc_valid": row["nfc_valid"] == "True",
        "threat_level": optional(row["threat_level"], str),
        "secondary_priority": optional(row["secondary_priority"], float),
        "secondary_resolution": optional(row['secondary_resolution'], str),
        "secondary_action": optional(row['secondary_action'], str),
        "secondary_ts": optional(row['secondary_ts'], parse_ts),
        "ticket_number": row['ticket_number'],
        "booth_id": row['booth_id'],
        "officer_badge": row['officer_badge'],
        "officer_name": row['officer_name'],
        "passport_number": row['passport_number'],
        "full_name": row['full_name'],
        "nationality": row['nationality'],
        "flight_code": row['flight_code'],
        "status": row['status'],
        "gate_action": row['gate_action'],
        "reason": row['reason']
    }

def prepare_statements(session):
    return {
        "by_passport": session.prepare(
            "INSERT INTO crossings_by_passport (passport_number, crossing_ts, crossing_id, full_name, nationality, booth_id, flight_code, status, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        "by_booth_day": session.prepare(
            "INSERT INTO crossings_by_booth_day (booth_id, crossing_date, crossing_ts, crossing_id, officer_badge, officer_name, passport_number, full_name, nationality, flight_code, biometric_match_score, nfc_valid, status, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        "alerts": session.prepare(
            "INSERT INTO alerts_by_day (crossing_date, crossing_ts, crossing_id, status, booth_id, officer_badge, officer_name, passport_number, full_name, nationality, flight_code, gate_action, threat_level, reason) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        "secondary": session.prepare(
            "INSERT INTO secondary_reviews_by_day (crossing_date, secondary_priority, crossing_ts, crossing_id, booth_id, ticket_number, passport_number, full_name, nationality, biometric_match_score, nfc_valid, reason, secondary_ts, secondary_resolution, secondary_action) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
        ),
        "stats": session.prepare(
            "UPDATE crossing_stats_by_day SET crossing_count = crossing_count + 1 "
            "WHERE crossing_date = ? AND status = ? AND nationality = ?"
        )
    }

def seed(session):
    statements = prepare_statements(session)
    session.execute("TRUNCATE crossing_stats_by_day")

    counts = {"by_passport": 0, "by_booth_day": 0, "alerts": 0, "secondary": 0, "stats": 0}

    with open(CSV_PATH, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            r = parse_row(row)

            session.execute(statements["by_passport"],(
                r["passport_number"], r["crossing_ts"], r["crossing_id"],
                r["full_name"], r["nationality"], r["booth_id"],
                r["flight_code"], r["status"], r["reason"],
            ))
            counts["by_passport"] += 1

            session.execute(statements["by_booth_day"],(
                r["booth_id"], r["crossing_date"], r["crossing_ts"], 
                r["crossing_id"], r["officer_badge"], r["officer_name"], 
                r["passport_number"], r["full_name"], r["nationality"], 
                r["flight_code"], r["biometric_match_score"], r["nfc_valid"], 
                r["status"], r["reason"],
            ))
            counts["by_booth_day"] += 1

            session.execute(statements["stats"], (r["crossing_date"], r["status"], r["nationality"]))
            counts["stats"] += 1

            if r["status"].startswith("DENIED_"):
                session.execute(statements["alerts"],(
                    r["crossing_date"], r["crossing_ts"], r["crossing_id"], 
                    r["status"], r["booth_id"], r["officer_badge"], 
                    r["officer_name"], r["passport_number"], r["full_name"], 
                    r["nationality"], r["flight_code"], r["gate_action"], 
                    r["threat_level"], r["reason"],
                ))
                counts["alerts"] += 1

            if r["status"] == "SECONDARY_INSPECTION":
                session.execute(statements["secondary"],(
                    r["crossing_date"], r["secondary_priority"], r["crossing_ts"], 
                    r["crossing_id"], r["booth_id"], r["ticket_number"], 
                    r["passport_number"], r["full_name"], r["nationality"], 
                    r["biometric_match_score"], r["nfc_valid"], r["reason"], 
                    r["secondary_ts"], r["secondary_resolution"], r["secondary_action"],
                ))
                counts["secondary"] += 1

    return counts

if __name__ == "__main__":
    cluster, session = get_cassandra_session()
    try:
        counts = seed(session)
        for table, n in counts.items():
            print(f"  {table}: {n} writes")
    finally:
        cluster.shutdown()