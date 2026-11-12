-- Queries
-- Q1: Crossing history of a passport (most recent first).
-- Example value: ESP-572524
SELECT full_name, nationality, crossing_ts, booth_id, flight_code, status, reason
FROM border_crossing.crossings_by_passport
WHERE passport_number = 'ESP-572524';

-- Q2: All crossings at a booth on a given day.
SELECT officer_name, officer_badge, full_name, nationality, passport_number, crossing_ts, flight_code, biometric_match_score, nfc_valid, status, reason
FROM border_crossing.crossings_by_booth_day
WHERE booth_id = 'BOX-007'
  AND crossing_date = '2026-10-21';

-- Q3: Crossings at a booth on a given day within a time range.
SELECT crossing_ts, officer_name, officer_badge, full_name, nationality, passport_number, flight_code, biometric_match_score, nfc_valid, status, reason
FROM border_crossing.crossings_by_booth_day
WHERE booth_id = 'BOX-007'
  AND crossing_date = '2026-10-21'
  AND crossing_ts >= '2026-10-21 06:00:00+0000'
  AND crossing_ts < '2026-10-21 14:00:00+0000';

-- Q4: Security alerts raised at booths on a given day (most recent).
SELECT crossing_ts, status, gate_action, booth_id, officer_name, officer_badge, full_name, nationality, passport_number, flight_code, threat_level, reason
FROM border_crossing.alerts_by_day
WHERE crossing_date = '2026-10-21';

-- Q5: Top-N most urgent secondary inspections on a given day.
SELECT secondary_priority, secondary_ts, secondary_resolution, secondary_action, crossing_ts, booth_id, full_name, nationality, passport_number, ticket_number, biometric_match_score, nfc_valid, reason
FROM border_crossing.secondary_reviews_by_day
WHERE crossing_date = '2026-10-21'
LIMIT 5;

-- Q6: Number of crossings by status and nationality on a given day.
SELECT status, nationality, crossing_count
FROM border_crossing.crossing_stats_by_day
WHERE crossing_date = '2026-10-21';