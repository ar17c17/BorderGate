-- Insertion examples
-- Q1: crossings_by_passport
INSERT INTO border_crossing.crossings_by_passport
    (passport_number, crossing_ts, crossing_id, full_name, nationality,
    booth_id, flight_code, status, reason)
VALUES
    ('ESP-11234', '2026-11-12 10:00:00+0000', b413d1c4-c943-40ee-a412-3898f7290735,
    'Javier Ruiz', 'ESP', 'BOX-001', 'AF-1400', 'DENIED_STOLEN_PASSPORT',
    'Passport flagged as stolen');

-- Q2, Q3: crossings_by_booth_day
INSERT INTO border_crossing.crossings_by_booth_day
    (booth_id, crossing_date, crossing_ts, crossing_id, officer_badge, officer_name,
    passport_number, full_name, nationality, flight_code,
    biometric_match_score, nfc_valid, status, reason)
VALUES
    ('BOX-001', '2026-11-12', '2026-11-12 10:00:00+0000', b413d1c4-c943-40ee-a412-3898f7290735,
    'CNP-8491', 'Carlos Gomez', 'ESP-11234', 'Javier Ruiz', 'ESP', 'AF-1400',
    0.91, true, 'DENIED_STOLEN_PASSPORT',
    'Passport flagged as stolen');

-- Q4: alerts_by_day (only DENIED_* crossings). threat_level omitted: not a wanted person.
INSERT INTO border_crossing.alerts_by_day
    (crossing_date, crossing_ts, crossing_id, status, booth_id, officer_badge, officer_name,
    passport_number, full_name, nationality, flight_code, gate_action, reason)
VALUES
    ('2026-11-12', '2026-11-12 10:00:00+0000', b413d1c4-c943-40ee-a412-3898f7290735,
    'DENIED_STOLEN_PASSPORT', 'BOX-001', 'CNP-8491', 'Carlos Gomez',
    'ESP-11234', 'Javier Ruiz', 'ESP', 'AF-1400', 'LOCK_GATE_IMMEDIATE',
    'Passport flagged as stolen');

-- Q5: secondary_reviews_by_day (a second passenger sent to secondary inspection)
-- priority = 90 * (1 - 0.52) = 43.2 ; approved because biometric >= 0.50
INSERT INTO border_crossing.secondary_reviews_by_day
    (crossing_date, secondary_priority, crossing_ts, crossing_id, booth_id, ticket_number,
    passport_number, full_name, nationality, biometric_match_score, nfc_valid, reason,
    secondary_ts, secondary_resolution, secondary_action)
VALUES
    ('2026-11-12', 43.2, '2026-11-12 10:05:00+0000', aebe8815-b21a-4542-939f-cbf482938ec0,
    'BOX-003', '002', 'CHE-900002', 'Jane Roe', 'CHE', 0.52, true,
    'Biometric threshold failed (Score: 0.52, NFC Valid: True)',
    '2026-11-12 10:18:00+0000', 'RESOLVED_APPROVED', 'SECONDARY_CLEARANCE_GRANTED');

-- Q6: crossing_stats_by_day (counter table: UPDATE, never INSERT)
UPDATE border_crossing.crossing_stats_by_day
SET crossing_count = crossing_count + 1
WHERE crossing_date = '2026-11-12' AND status = 'DENIED_STOLEN_PASSPORT' AND nationality = 'ESP';

-- Verification
SELECT crossing_ts, full_name, nationality, booth_id, status FROM border_crossing.crossings_by_passport
WHERE passport_number = 'ESP-11234';

SELECT crossing_ts, status, threat_level, gate_action FROM border_crossing.alerts_by_day
WHERE crossing_date = '2026-11-12';

SELECT status, nationality, crossing_count FROM border_crossing.crossing_stats_by_day
WHERE crossing_date = '2026-11-12';

SELECT secondary_priority, full_name, secondary_resolution FROM border_crossing.secondary_reviews_by_day
WHERE crossing_date = '2026-11-12';