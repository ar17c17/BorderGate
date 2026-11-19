import time
import sys
from datetime import date, datetime, timezone
from config.cassandra_client import get_cassandra_session

# List of dicts with the queries with the CQL code and the value for ? in the CQL code
QUERIES = [
    {
        "id": "Q1",
        "description": "Crossing history of a passport (most recent first).",
        "cql": "SELECT full_name, nationality, crossing_ts, booth_id, flight_code, status, reason "
                "FROM border_crossing.crossings_by_passport "
                "WHERE passport_number = ?",
        "values": ('ESP-572524',),
    },
    {
        "id": "Q2",
        "description": "All crossings at a booth on a given day (chronological order).",
        "cql": "SELECT officer_name, officer_badge, full_name, nationality, passport_number, crossing_ts, flight_code, biometric_match_score, nfc_valid, status, reason "
                "FROM border_crossing.crossings_by_booth_day "
                "WHERE booth_id = ? AND crossing_date = ?",
        "values": ('BOX-007', date(2026, 10, 21),),
    },
    {
        "id": "Q3",
        "description": "Crossings at a booth on a given day within a time range.",
        "cql": "SELECT crossing_ts, officer_name, officer_badge, full_name, nationality, passport_number, flight_code, biometric_match_score, nfc_valid, status, reason "
                "FROM border_crossing.crossings_by_booth_day "
                "WHERE booth_id = ? AND crossing_date = ? AND crossing_ts >= ? AND crossing_ts < ?",
        "values": ('BOX-007', date(2026, 10, 21),
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

# Function to run the queries n times and save the time of execution.
# Default n = 5
def run_query(session, statement, values, n=5):
    times = []
    for _ in range(n):
        start = time.perf_counter()
        # To measure the time for all the execution we store the rows in list format
        rows = list(session.execute(statement, values))
        times.append((time.perf_counter() - start) * 1000)
    return rows, times

# Format each value to show it short and clean in the table.
def format_value(value):
    if value is None:
        return "-"
    if isinstance(value, datetime):
        return value.strftime("%Y-%m-%d %H:%M")
    if isinstance(value, float):
        return f"{value:.2f}"
    text = str(value)
    return text if len(text) <= 30 else text[:27] + "..."


# Print the rows of a query as an aligned table.
def print_rows(q, rows, max_rows=10):
    print(f" {q['id']} | {q['description']}")
    if not rows:
        print("(no rows)\n")
        return

    columns = rows[0]._fields
    data = [[format_value(v) for v in row] for row in rows[:max_rows]]
    widths = [max(len(col), *(len(r[i]) for r in data)) for i, col in enumerate(columns)]
    line = "+" + "+".join("-" * (w + 2) for w in widths) + "+"
    print(line)
    print("| " + " | ".join(col.ljust(w) for col, w in zip(columns, widths)) + " |")
    print(line)

    for r in data:
        print("| " + " | ".join(v.ljust(w) for v, w in zip(r, widths)) + " |")
    print(line)

    if len(rows) > max_rows:
        print(f"... {len(rows) - max_rows} more rows")
    print()

# Start the program.
if __name__ == "__main__":
    cluster, session = get_cassandra_session()
    result = []

    # Arguments for execution, queries and verbose options.
    args = sys.argv[1:]
    verbose = not args or "-v" in args or "--verbose" in args
    selected = [arg.upper() for arg in args if not arg.startswith("-")]
    queries = [q for q in QUERIES if q['id'] in selected] if selected else QUERIES

    if not queries:
        print(f"Unknown query: {' '.join(selected)}. Use Q1-Q6")
        cluster.shutdown()
        sys.exit(1)

    try:
        for q in queries:
            statement = session.prepare(q['cql'])
            # We execute the query 50 times to get the mean and the minimum and reduce the noise of the 
            # execution because the first is slower than the others.
            rows, times = run_query(session, statement, q['values'], 50)
            result.append((q, rows, times))

            # Print each query output only in verbose mode
            if verbose:
                print_rows(q, rows)

        print(f"{'Q':<4}{'Rows':>6}{'Avg (ms)':>11}{'Min (ms)':>11} Description")
        for q, rows, times in result:
            print(f"{q['id']:<4}{len(rows):>6}{sum(times)/len(times):>11.2f}{min(times):>11.2f} {q['description']}")

    finally:
        # End the connection of cassandra.
        cluster.shutdown()
