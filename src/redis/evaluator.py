# -----------------------------------------------------------------------------
# Module: evaluator.py
# Purpose: Implements the evaluation logic to return a decision. Called by 'consumer.py'.
# -----------------------------------------------------------------------------
import json
def evaluate_passenger(passenger,r_cloud):
    """
    Evaluates passenger credentials against Redis Cloud security policies.
    Returns a decision with status, decision reason, and priority.
    """

    passport = passenger.get("passport_number")
    nationality = passenger.get("nationality")
    biometric_score = float(passenger.get("biometric_match_score"))
    nfc_valid = bool(passenger.get("nfc_valid"))
    has_visa = bool(passenger.get("has_visa"))

    # Check stolen passports blacklist (SET)
    if r_cloud.sismember("blacklist:stolen_passports", passport):
            stolen_details = r_cloud.hgetall(f"stolen:{passport}")
            return {
                "status": "DENIED_STOLEN_PASSPORT",
                "reason": "Passport flagged as stolen ",
                "details": stolen_details,
                "action": "LOCK_GATE_IMMEDIATE"
            }

    # Check Wanted Persons List (ZSET)
    threat_score = r_cloud.zscore("blacklist:wanted_persons", passport)
    if threat_score is not None:
        wanted_details = r_cloud.hgetall(f"wanted:{passport}")
        return {
            "status": "DENIED_WANTED_PERSON",
            "reason": f"Active arrest warrant (Threat Score: {int(threat_score)})",
            "details": wanted_details,
            "action": "LOCK_GATE_AND_NOTIFY"
        }

    # Physical Document & Biometric Checks
    if not nfc_valid or biometric_score < 0.7:
        priority = 0
        if not nfc_valid:
             priority = 10
        priority += 90 * (1 - biometric_score)
        return {
            "status": "SECONDARY_INSPECTION",
            "reason": f"Biometric threshold failed (Score: {biometric_score}, NFC Valid: {nfc_valid})",
            "details": {"biometric_score": biometric_score, "nfc_valid": nfc_valid},
            "action": "REDIRECT_TO_SECONDARY",
            "priority":  priority
        }
    
    visa_policy = r_cloud.hgetall(f"policy:visa:{nationality}")
    requires_visa = visa_policy.get("requires_visa")
         
    if requires_visa and not has_visa:
        return {
            "status": "DENIED_NO_VISA",
            "reason": f"Visa required for nationality {nationality} but no valid visa presented",
            "action": "LOCK_GATE",
        }
    # Access Granted
    return {
        "status": "APPROVED",
        "reason": "Clear security checks",
        "details": {},
        "action": "OPEN_GATE"
    }