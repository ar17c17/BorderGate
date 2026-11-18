import time
from datetime import date, datetime, timezone
from config.cassandra_client import get_cassandra_session

QUERIES = [
    {
        "id": "Q1",
        "description": "Crossing history of a passport (most recent first).",
        "cql": "SELECT full_name, nationality, crossing_ts, booth_id, flight_code, status, reason "
                "FROM border_crossing.crossings_by_passport "
                "WHERE passport_number = ?",
        "values": ("ESP-572524",),
    },
    {
        "id": "Q2",
        "description": "All crossings at a booth on a given day (chronological order).",
        "cql": "SELECT officer_name, officer_badge, full_name, nationality, passport_number, crossing_ts, flight_code, biometric_match_score, nfc_valid, status, reason "
                "FROM border_crossing.crossings_by_booth_day "
                "WHERE booth_id = ? AND crossing_date = ?",
        "values": ("BOX-007", date(2026, 10, 21),),
    },
    {
        "id": "Q3",
        "description": "Crossings at a booth on a given day within a time range.",
        "cql": "SELECT crossing_ts, officer_name, officer_badge, full_name, nationality, passport_number, flight_code, biometric_match_score, nfc_valid, status, reason "
                "FROM border_crossing.crossings_by_booth_day "
                "WHERE booth_id = ? AND crossing_date = ? AND crossing_ts >= ? AND crossing_ts < ?",
        "values": ("BOX-007", date(2026, 10, 21),
                    datetime(2026, 10, 21, 6, 0, tzinfo=timezone.utc),
                    datetime(2026, 10, 21, 14, 0, tzinfo=timezone.utc),),
    },
    {
        "id": "Q4",
        "description": "Security alerts raised at booths on a given day (most recent first).",
        "cql": "SELECT crossing_ts, status, gate_action, booth_id, officer_name, officer_badge, full_name, nationality, passport_number, flight_code, threat_level, reason "
                "FROM border_crossing.alerts_by_day "
                "WHERE crossing_date = ?",
        "values": (date(2026, 10, 21),),
    },
    {
        "id": "Q5",
        "description": "Top-N most urgent secondary inspections on a given day.",
        "cql": "SELECT secondary_priority, secondary_ts, secondary_resolution, secondary_action, crossing_ts, booth_id, full_name, nationality, passport_number, ticket_number, biometric_match_score, nfc_valid, reason "
                "FROM border_crossing.secondary_reviews_by_day "
                "WHERE crossing_date = ? "
                "LIMIT ?",
        "values": (date(2026, 10, 21), 5,),
    },
    {
        "id": "Q6",
        "description": "Number of crossings by status and nationality on a given day.",
        "cql": "SELECT status, nationality, crossing_count "
                "FROM border_crossing.crossing_stats_by_day "
                "WHERE crossing_date = ?",
        "values": (date(2026, 10, 21),),
    },
]

def run_query(session, statement, values, n=5):
    times = []
    for _ in range(n):
        start = time.perf_counter()
        rows = list(session.execute(statement, values))
        times.append((time.perf_counter() - start) * 1000)
    return rows, times

if __name__ == "__main__":
    cluster, session = get_cassandra_session()
    try:
        print(f"{'Q':<4}{'Rows':>6}{'Avg (ms)':>11}{'Min (ms)':>11} Description")
        for q in QUERIES:
            statement = session.prepare(q['cql'])
            rows, times = run_query(session, statement, q['values'], 50)
            print(f"{q['id']:<4}{len(rows):>6}{sum(times)/len(times):>11.2f}{min(times):>11.2f} {q['description']}")

    finally:
        cluster.shutdown()
