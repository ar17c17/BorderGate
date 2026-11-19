-- -----------------------------------------------------------------------------
-- File: schema.cql
-- Purpose: Creates the border_crossing keyspace and query-driven denormalized tables for Q1-Q6
-- -----------------------------------------------------------------------------

-- Create keyspace.
CREATE KEYSPACE IF NOT EXISTS "border_crossing" 
WITH REPLICATION = {
'class' : 'NetworkTopologyStrategy',
'Mad_Barajas' : 1
};

-- Create tables.
-- Q1: Crossing history of a passport (most recent first).
CREATE TABLE IF NOT EXISTS "border_crossing"."crossings_by_passport" (
  "passport_number" text,
  "crossing_ts" timestamp,
  "crossing_id" uuid,
  "full_name" text STATIC,
  "nationality" text STATIC,
  "booth_id" text,
  "flight_code" text,
  "status" text,
  "reason" text,
  PRIMARY KEY ("passport_number", "crossing_ts", "crossing_id")
)
WITH CLUSTERING ORDER BY ("crossing_ts" DESC, "crossing_id" ASC);

-- Q2: All crossings at a booth on a given day (chronological order).
-- Q3: Crossings at a booth on a given day within a time range.
CREATE TABLE IF NOT EXISTS "border_crossing"."crossings_by_booth_day" (
  "booth_id" text,
  "crossing_date" date,
  "crossing_ts" timestamp,
  "crossing_id" uuid,
  "officer_badge" text,
  "officer_name" text,
  "passport_number" text,
  "full_name" text,
  "nationality" text,
  "flight_code" text,
  "biometric_match_score" double,
  "nfc_valid" boolean,
  "status" text,
  "reason" text,
  PRIMARY KEY (("booth_id", "crossing_date"), "crossing_ts", "crossing_id")
)
WITH CLUSTERING ORDER BY ("crossing_ts" ASC, "crossing_id" ASC);

-- Q4: Security alerts raised at booths on a given day (most recent first).
CREATE TABLE IF NOT EXISTS "border_crossing"."alerts_by_day" (
  "crossing_date" date,
  "crossing_ts" timestamp,
  "crossing_id" uuid,
  "status" text,
  "booth_id" text,
  "officer_badge" text,
  "officer_name" text,
  "passport_number" text,
  "full_name" text,
  "nationality" text,
  "flight_code" text,
  "gate_action" text,
  "threat_level" text,
  "reason" text,
  PRIMARY KEY ("crossing_date", "crossing_ts", "crossing_id")
)
WITH CLUSTERING ORDER BY ("crossing_ts" DESC, "crossing_id" ASC);

-- Q5: Top-N most urgent secondary inspections on a given day.
CREATE TABLE IF NOT EXISTS "border_crossing"."secondary_reviews_by_day" (
  "crossing_date" date,
  "secondary_priority" double,
  "crossing_ts" timestamp,
  "crossing_id" uuid,
  "booth_id" text,
  "ticket_number" text,
  "passport_number" text,
  "full_name" text,
  "nationality" text,
  "biometric_match_score" double,
  "nfc_valid" boolean,
  "reason" text,
  "secondary_ts" timestamp,
  "secondary_resolution" text,
  "secondary_action" text,
  PRIMARY KEY ("crossing_date", "secondary_priority", "crossing_ts", "crossing_id")
)
WITH CLUSTERING ORDER BY ("secondary_priority" DESC, "crossing_ts" ASC, "crossing_id" ASC);

-- Q6: Number of crossings by status and nationality on a given day.
CREATE TABLE IF NOT EXISTS "border_crossing"."crossing_stats_by_day" (
  "crossing_date" date,
  "status" text,
  "nationality" text,
  "crossing_count" counter,
  PRIMARY KEY ("crossing_date", "status", "nationality")
)
WITH CLUSTERING ORDER BY ("status" ASC, "nationality" ASC);