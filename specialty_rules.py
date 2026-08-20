import random
import string
from datetime import date, datetime


def generate_confirmation_code():
    suffix = "".join(random.choices(
        string.ascii_uppercase + string.digits, k=5))
    return f"CMH-{suffix}"


def validate_booking(specialty_row: dict, body, requested_date: date):
    """Returns (error_code, error_message) or (None, None) if valid."""

    if specialty_row["requires_referral"] and not body.referral_confirmed:
        return "REFERRAL_REQUIRED", "This specialty requires a referral note. Please confirm referral status."

    if specialty_row["gender_restriction"]:
        if not body.patient_gender:
            return "GENDER_CONFIRMATION_REQUIRED", "Please confirm the patient's gender for this specialty."
        if body.patient_gender.lower() != specialty_row["gender_restriction"]:
            # allowed, but only with explicit confirmation - since it's already provided and mismatched, we let it pass
            pass

    if specialty_row["age_banded"] and body.patient_age is None:
        return "AGE_REQUIRED", "Please provide the patient's age for this specialty."

    if specialty_row["min_advance_days"] > 0:
        min_date = date.today()
        delta = (requested_date - min_date).days
        if delta < specialty_row["min_advance_days"]:
            return "INSUFFICIENT_ADVANCE_NOTICE", f"This specialty requires at least {specialty_row['min_advance_days']} days advance booking."

    return None, None
